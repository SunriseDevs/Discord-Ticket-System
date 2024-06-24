# Import Libraries For Ticket Bot
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import os
from datetime import datetime
import random
import string
import asyncio

# Use intents And you can change intents
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.reactions = True
intents.members = True

# Set prefix Or you can change prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Set role-id And channel-id
owner_id = 1223343577770229830  # Replace with your Discord user ID
supporter_role_id = 1223343577770229829  # Replace with the ID of the supporter role
channel_id = 1252257833651802133  # Replace with the channel ID where you want to send the button
log_channel_id = 1252303124006178887  # Replace with the channel ID where you want to send the log files
activity_log_channel_id = 1252374292935737344  # Replace with the channel ID where you want to log ticket activities
notification_channel_id = 1252381885338877952  # Replace with the channel ID where you want to send the notification

# Category IDs for different priority levels
low_priority_category_id = 1252386686403477685
medium_priority_category_id = 1252386787511238657
high_priority_category_id = 1252386817148190853

# For create the ticket
class CreateTicketButton(Button):
    def __init__(self):
        super().__init__(label='Create Ticket', style=discord.ButtonStyle.primary) # You can edit text button

    async def callback(self, interaction):
        guild = interaction.guild
        user = interaction.user
        view = TicketCategoryView()
        await interaction.response.send_message('Select a category:', view=view, ephemeral=True) # You can edit text dropdown menu

# For view ticket category
class TicketCategoryView(View):
    def __init__(self):
        super().__init__()
        self.select = Select(
            placeholder="Select a category", # You can edit text place holder
            min_values=1,
            max_values=1,
            options=[ # You can create select option with label and description
                discord.SelectOption(label="Product", description="Product Support"),
                discord.SelectOption(label="Website", description="Website Support"),
                discord.SelectOption(label="Server", description="Server Support")
            ]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction):
        category = self.select.values[0]
        view = TicketPriorityView(category)
        await interaction.response.send_message('Select the priority:', view=view, ephemeral=True) # You can edit text priority selection

# For view ticket priority catogory
class TicketPriorityView(View):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.select = Select(
            placeholder="Select a priority", # You can edit text selection dropdown menu
            min_values=1,
            max_values=1,
            options=[ # You can create select option with label and description 
                discord.SelectOption(label="Low", description="Low Priority"),
                discord.SelectOption(label="Medium", description="Medium Priority"),
                discord.SelectOption(label="High", description="High Priority")
            ]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction):
        priority = self.select.values[0]
        # Set priority catgory for create ticket channel
        if priority == "Low":
            category_id = low_priority_category_id
        elif priority == "Medium":
            category_id = medium_priority_category_id
        elif priority == "High":
            category_id = high_priority_category_id

        category = self.category
        # Generate a random channel name
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        channel_name = f'ticket-{random_string}-{category.lower()}'

        category_channel = bot.get_channel(category_id)
        if not category_channel:
            await interaction.response.send_message(f'Category channel with ID {category_id} not found.', ephemeral=True)
            return

        channel = await category_channel.create_text_channel(channel_name)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        supporter_role = interaction.guild.get_role(supporter_role_id)
        if supporter_role:
            await channel.set_permissions(supporter_role, read_messages=True, send_messages=True)
        await channel.set_permissions(interaction.guild.default_role, read_messages=False, send_messages=False)

        embed = discord.Embed(title='New Ticket Created', description=f'Hello {interaction.user.mention}! Your ticket has been created in {priority} priority. Please describe your issue And Wait To Supporter Answer You !', color=0x00ff00)

        close_button_view = View()
        close_button = Button(label="Close Ticket", style=discord.ButtonStyle.danger)
        close_button.callback = lambda i: self.close_ticket_callback(i, supporter_role_id)
        close_button_view.add_item(close_button)

        await channel.send(embed=embed, view=close_button_view)
        await interaction.response.send_message(f'Ticket created in {channel.mention}!', ephemeral=True)

        # Log the creation of the ticket
        activity_log_channel = bot.get_channel(activity_log_channel_id)
        if activity_log_channel:
            opened_embed = discord.Embed(title='Ticket Opened', description=f'Ticket {channel.mention} was opened by {interaction.user.mention} in category {category} with {priority} priority.', color=0x00ff00)
            await activity_log_channel.send(embed=opened_embed)

        # Notify in the notification channel
        notification_channel = bot.get_channel(notification_channel_id)
        if notification_channel:
            await notification_channel.send(f'@everyone, a new {priority} priority ticket has been created by {interaction.user.mention} in {channel.mention}. Please check it out!')

        # Start the inactivity timer
        await self.start_inactivity_timer(channel, interaction.user)

    async def start_inactivity_timer(self, channel, user):
        def check(msg):
            return msg.channel == channel and msg.author == user

        try:
            await bot.wait_for('message', timeout=600, check=check)  # Wait for 10 minutes
        except asyncio.TimeoutError:
            await self.close_ticket_due_to_inactivity(channel)

    async def close_ticket_due_to_inactivity(self, channel):
        messages = [message async for message in channel.history(limit=None)]
        current_date = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        file_path = f'ticket-{channel.name}-{current_date}.txt'
        with open(file_path, 'w', encoding='utf-8') as f:
            for message in messages:
                f.write(f'{message.author.name}: {message.clean_content}\n')

        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            with open(file_path, 'rb') as f:
                await log_channel.send(file=discord.File(f, file_path))

        await channel.delete()
        closed_embed = discord.Embed(title='Ticket Closed Due to Inactivity', description='Your ticket has been closed due to inactivity.', color=0xff0000)
        await log_channel.send(embed=closed_embed)

        # Log the closure due to inactivity
        activity_log_channel = bot.get_channel(activity_log_channel_id)
        if activity_log_channel:
            inactivity_embed = discord.Embed(title='Ticket Closed', description=f'Ticket {channel.name} was closed due to inactivity.', color=0xff0000)
            await activity_log_channel.send(embed=inactivity_embed)

        # Optionally, you can delete the local file after sending it to the log channel
        os.remove(file_path)

    async def close_ticket_callback(self, interaction, supporter_role_id):
        channel = interaction.channel
        supporter_role = channel.guild.get_role(supporter_role_id)
        confirm_embed = discord.Embed(title='Confirm Ticket Closure', description='Are you sure you want to close this ticket?', color=0xff0000)
        confirm_button = Button(label='Confirm', style=discord.ButtonStyle.danger)
        cancel_button = Button(label='Cancel', style=discord.ButtonStyle.primary)

        async def confirm_callback(interaction):
            messages = [message async for message in channel.history(limit=None)]
            current_date = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            file_path = f'ticket-{channel.name}-{current_date}.txt'
            with open(file_path, 'w', encoding='utf-8') as f:
                for message in messages:
                    f.write(f'{message.author.name}: {message.clean_content}\n')

            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                with open(file_path, 'rb') as f:
                    await log_channel.send(file=discord.File(f, file_path))

            await channel.delete()
            closed_embed = discord.Embed(title='Ticket Closed', description=f'Ticket {channel.name} was closed by {interaction.user.mention}.', color=0xff0000)
            await interaction.response.send_message(embed=closed_embed, ephemeral=True)

            # Log the closure
            activity_log_channel = bot.get_channel(activity_log_channel_id)
            if activity_log_channel:
                closed_embed = discord.Embed(title='Ticket Closed', description=f'Ticket {channel.name} was closed by {interaction.user.mention}.', color=0xff0000)
                await activity_log_channel.send(embed=closed_embed)

            # Optionally, you can delete the local file after sending it to the log channel
            os.remove(file_path)

        async def cancel_callback(interaction):
            await interaction.response.send_message('Ticket closure cancelled.', ephemeral=True)

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view = View()
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(embed=confirm_embed, view=view)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')

    # Send a message to the channel with the button
    channel = bot.get_channel(channel_id)
    embed = discord.Embed(title='Create a Ticket', description='Click the button below to create a new ticket.', color=0x00ff00)
    view = View()
    view.add_item(CreateTicketButton())
    await channel.send(embed=embed, view=view)

    # Create or fetch the log channels
    log_channel = bot.get_channel(log_channel_id)
    activity_log_channel = bot.get_channel(activity_log_channel_id)

    if log_channel is None:
        log_channel = await bot.fetch_channel(log_channel_id)
    if activity_log_channel is None:
        activity_log_channel = await bot.fetch_channel(activity_log_channel_id)

    if log_channel is not None:
        await log_channel.send('Bot is online and ready to log ticket files.')
    if activity_log_channel is not None:
        await activity_log_channel.send('Bot is online and ready to log ticket activities.')

bot.run('TOKEN')