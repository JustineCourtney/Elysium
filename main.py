# -*- coding: utf-8 -*-
import os
from datetime import datetime
import discord
from discord.ext import commands
from abilities import apply_sqlite_migrations
from sqlalchemy.orm import Session
from web import keep_alive
from models import Base, engine, UserPoints, RoleHierarchy, Session as SessionMaker

def generate_oauth_link(client_id):
    base_url = "https://discord.com/api/oauth2/authorize"
    redirect_uri = "http://localhost"
    scope = "bot"
    permissions = "8"  # Administrator permission for simplicity
    return "{0}?client_id={1}&permissions={2}&scope={3}".format(
        base_url, client_id, permissions, scope
    )

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

def get_points_info(points):
    next_threshold = ((points // 3) + 1) * 3
    points_needed = next_threshold - points
    return "Current points: {0}\nPoints needed for next role: {1}".format(points, points_needed)

@bot.command(name='add_points')
def add_points(ctx, user: discord.Member, points: int):
    if not ctx.author.guild_permissions.administrator:
        ctx.send("Only administrators can add points!")
        return
    
    if points <= 0:
        ctx.send("Please provide a positive number of points!")
        return
    
    session = SessionMaker()
    try:
        user_points = session.query(UserPoints).filter_by(user_id=user.id).first()
        
        if not user_points:
            user_points = UserPoints(user_id=user.id, points=points)
            session.add(user_points)
        else:
            user_points.points += points
        
        user_points.last_updated = datetime.utcnow()
        session.commit()
        
        # Update roles
        role_hierarchy = session.query(RoleHierarchy).order_by(RoleHierarchy.point_threshold).all()
        
        if not role_hierarchy:
            ctx.send("Role hierarchy not configured. Use !configure_roles first.")
            return
        
        current_role = None
        for role_config in role_hierarchy:
            if user_points.points >= role_config.point_threshold:
                current_role = role_config.role_name
        
        if current_role:
            guild_roles = {role.name: role for role in ctx.guild.roles}
            
            for role_config in role_hierarchy:
                if role_config.role_name in guild_roles and role_config.role_name != current_role:
                    role_to_remove = guild_roles[role_config.role_name]
                    if role_to_remove in user.roles:
                        user.remove_roles(role_to_remove)
            
            new_role = guild_roles.get(current_role)
            if new_role and new_role not in user.roles:
                user.add_roles(new_role)
                ctx.send("{0} has been promoted to {1}!".format(user.mention, current_role))
        
        info = get_points_info(user_points.points)
        ctx.send("Added {0} points to {1}!\n{2}".format(points, user.mention, info))
    
    except Exception as e:
        print("Error: {0}".format(e))
        ctx.send("An error occurred while adding points.")
    finally:
        session.close()

@bot.command(name='points')
def check_points(ctx):
    session = SessionMaker()
    try:
        user_points = session.query(UserPoints).filter_by(user_id=ctx.author.id).first()
        
        if not user_points:
            ctx.send("You don't have any points yet!")
            return
        
        info = get_points_info(user_points.points)
        ctx.send(info)
    finally:
        session.close()

@bot.command(name='configure_roles')
def configure_roles(ctx, role_name: str, point_threshold: int):
    if not ctx.author.guild_permissions.administrator:
        ctx.send("Only administrators can configure roles!")
        return
    
    if point_threshold < 0:
        ctx.send("Point threshold must be positive!")
        return
    
    session = SessionMaker()
    try:
        # Validate role exists
        guild_roles = {role.name: role for role in ctx.guild.roles}
        if role_name not in guild_roles:
            ctx.send("Role '{0}' does not exist in this server!".format(role_name))
            return
        
        # Add or update role in hierarchy
        role_entry = session.query(RoleHierarchy).filter_by(role_name=role_name).first()
        if role_entry:
            role_entry.point_threshold = point_threshold
        else:
            new_order = session.query(RoleHierarchy).count() + 1
            role_entry = RoleHierarchy(
                role_name=role_name,
                point_threshold=point_threshold,
                order=new_order
            )
            session.add(role_entry)
        
        session.commit()
        ctx.send("Role '{0}' configured with {1} point threshold!".format(role_name, point_threshold))
    
    except Exception as e:
        print("Error: {0}".format(e))
        ctx.send("An error occurred while configuring roles.")
    finally:
        session.close()

@bot.event
def on_ready():
    print("Bot is ready. Logged in as {0}".format(bot.user))
    print("Bot invite link: {0}".format(generate_oauth_link(os.environ.get('CLIENT_ID'))))

def main():
    apply_sqlite_migrations(engine, Base, 'migrations')
    
    client_id = os.environ.get('CLIENT_ID')
    bot_token = os.environ.get('BOT_TOKEN')
    
    if not client_id or not bot_token:
        print("Missing required environment variables!")
        return
    
    keep_alive()  # Start the web server
    bot.run(bot_token)

if __name__ == "__main__":
    main()