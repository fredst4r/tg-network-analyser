#!/usr/bin/env python3

# Import packages from requirements.txt
import argparse
import configparser
import csv
import re
import asyncio
import nest_asyncio
import pandas as pd
import requests
import pip_system_certs.wrapt_requests
import plotly.graph_objects as go
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import PeerChannel
from tqdm.asyncio import tqdm
from tqdm import tqdm as tqdm_sync

def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')

    if 'Telegram' not in config:
        raise ValueError("Missing 'Telegram' section in the config file.")

    api_id = config['Telegram'].get('api_id')
    api_hash = config['Telegram'].get('api_hash')
    phone = config['Telegram'].get('phone')
    username = config['Telegram'].get('username')
    channel_usernames = config['Telegram'].get('channel_usernames', '').split(',')

    return api_id, api_hash, phone, username, channel_usernames

api_id, api_hash, phone, username, channel_usernames = read_config()

# Use the api_id and api_hash to create the TelegramClient instance
client = TelegramClient('anon', api_id, api_hash)

# Regex to match URLs including Telegram links
url_pattern = re.compile(r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|t\.me/[a-zA-Z0-9_]+)')

print(f"Scraping messages from {len(channel_usernames)} target channels...")

# Apply nest_asyncio
nest_asyncio.apply()

async def get_channel_username_by_id(channel_id):
    """
    Fetch the username of a channel by its ID.

    Parameters:
    channel_id (int): The ID of the channel.

    Returns:
    str: The username of the channel or an error message.
    """
    try:
        entity = await client.get_entity(PeerChannel(channel_id))
        return entity.username
    except Exception as e:
        error_message = f"Error fetching username for channel ID {channel_id}: {e}"
        return error_message

async def get_channel_info(channel_username):
    """
    Fetch detailed information about a channel.

    Parameters:
    channel_username (str): The username of the channel.

    Returns:
    object: Full channel information or an error message.
    """
    try:
        entity = await client.get_entity(channel_username)
        full_channel = await client(GetFullChannelRequest(channel=entity))
        return full_channel
    except Exception as e:
        error_message = f"Error fetching channel info for {channel_username}: {e}"
        return error_message

async def get_all_messages(channel_username, master_writer):
    """
    Fetch all messages from a channel and write them to a CSV file.

    Parameters:
    channel_username (str): The username of the channel.
    master_writer (csv.writer): The CSV writer object to write messages to.
    """
    await client.start()
    entity = await client.get_entity(channel_username)
    offset_id = 0
    limit = 100  # Increase the limit to fetch more messages at once
    all_messages = []
    total_messages = 0
    
    # Initialize the progress bar with unknown total
    progress_bar = tqdm(desc=f"Scraping {channel_username} for messages", unit=" message", dynamic_ncols=True)

    while True:
        try:
            history = await client(GetHistoryRequest(
                peer=entity,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0
            ))
            await asyncio.sleep(1)  # Wait for 1 second between requests
            if not history.messages:
                break

            messages = history.messages
            for message in messages:
                all_messages.append(message.to_dict())
            
            # Update the total for the progress bar based on the latest message ID
            if progress_bar.total is None or messages[0].id > progress_bar.total:
                progress_bar.total = messages[0].id
                progress_bar.refresh()

            offset_id = messages[len(messages) - 1].id
            total_messages = len(all_messages)
            progress_bar.update(len(messages))
        except Exception as e:
            print(f"Error occurred: {e}")
            await asyncio.sleep(5)  # Wait for 5 seconds before trying again

    if progress_bar is not None:
        progress_bar.close()

    url_pattern = re.compile(r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|t\.me/[a-zA-Z0-9_]+)')

    if all_messages:
        print(f"Writing {all_messages[0]['id']} messages from {channel_username} to the master CSV file")
    
    for message in all_messages:
        text = message.get('message', '')
        if text:  # Only process and write rows where the message is not empty
            urls = url_pattern.findall(text)
            filtered_urls = [url for url in urls if f't.me/{channel_username}' not in url]  # Change this to the target channel username you want to filter

            # Initialize fwd_from_info to None
            fwd_from_info = None

            # Check for forwarded messages
            from_id = None
            fwd_from = message.get('fwd_from', None)
            if fwd_from and 'from_id' in fwd_from:
                from_id = fwd_from.get('from_id', None)
                if from_id and from_id.get('_') == 'PeerChannel':
                    fwd_from_channel_id = from_id.get('channel_id')
                    fwd_from_info = await get_channel_username_by_id(fwd_from_channel_id)
                    if fwd_from_info and not fwd_from_info.startswith("Error fetching username"):
                        fwd_from_info = fwd_from_info

            # Extract view count, forward count, and reply count
            views = message.get('views', '')
            forwards = message.get('forwards', '')
            replies = message.get('replies', {}).get('replies', '') if message.get('replies') else ''

            # Write the message to the master CSV file
            master_writer.writerow([channel_username, message['id'], message['date'], text, ', '.join(filtered_urls), fwd_from_info, views, forwards, replies])

async def main():
    """
    Main function to scrape messages from target channels and perform social network analysis.
    """
    # Create a master CSV file
    with open('master_messages.csv', mode='w', encoding='utf-8') as master_file:
        master_writer = csv.writer(master_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        master_writer.writerow(['channel_username', 'id', 'date', 'message', 'url', 'forwarded_from', 'views', 'forwards', 'replies'])

        for channel_username in channel_usernames:
            await get_all_messages(channel_username, master_writer)
            print(f"Finished scraping messages from channel {channel_username}...")
    
    # Read the CSV file
    df = pd.read_csv('master_messages.csv')

    # Get the total number of messages
    total_messages = df.shape[0]

    print(f"Finished scraping messages from all channels and transferring them to the master CSV file. The total number of messages scraped was {total_messages}")

    print("Transforming the scraped messages into a social network analysis dataset and analysing the results...")

    # Remove rows with no value in the forwarded_from column
    df = df.dropna(subset=['forwarded_from'])

    # Remove rows with error messages in the forwarded_from column
    error_message_pattern = re.compile(r"Error fetching username for channel ID \d+: .+")
    df = df[~df['forwarded_from'].str.contains(error_message_pattern)]

    # Rename the columns
    df = df.rename(columns={'channel_username': 'source', 'forwarded_from': 'target'})
    sna_total_messages = df.shape[0]

    print(f"Dataset has been successfully created for social network analysis! There are a total of {sna_total_messages} forwarded messages in the dataset.")

    # Count the occurrences of each unique value in the "target" column
    target_counts = df['target'].value_counts()

    # Get all targets instead of just the top 30
    all_targets = target_counts.index

    # Create a dictionary to store the share of each channel for each target
    analysis_results = []

    # Add a progress bar for iterating over all targets
    for target in tqdm_sync(all_targets, desc="Processing all targets", unit=" target"):
        try:
            target_data = {'target': target, 'total_shares': target_counts[target]}
            
            # Fetch the channel info
            channel_info = await get_channel_info(target)
            if channel_info and not isinstance(channel_info, str):
                target_data['subscribers'] = channel_info.full_chat.participants_count

            df_target = df[df['target'] == target]
            source_counts = df_target['source'].value_counts()
            for source in source_counts.index:
                share_percentage = (source_counts[source] / target_counts[target]) * 100
                target_data[source] = f"{share_percentage:.2f}% ({source_counts[source]} messages)"
            analysis_results.append(target_data)
        except ValueError as ve:
            if "No user has" in str(ve):
                print(f"User not found for target {target}. Skipping...")
            else:
                raise  # Re-raise the exception if it's a different ValueError
        except Exception as e:
            print(f"An error occurred with target {target}: {e}. Continuing with the next target.")
            continue

        # Fetch the total views for the target channel
        #total_views = await get_total_views(target)
        #target_data['total_views'] = total_views

    # Convert the analysis results to a DataFrame
    analysis_df = pd.DataFrame(analysis_results)

    # Save the analysis results to a CSV file
    analysis_df.to_csv('analysis-results.csv', index=False)

    print("Analysis results have been saved to the analysis-results CSV file!")

    print("Social network analysis completed successfully!")

    analysis_results = f'''
    Here are the results:

    1) A total of {len(channel_usernames)} target channels were scraped for messages

    2) A total of {total_messages} messages were scraped from the target channels

    3) A total number of {len(all_targets)} forwarded channels were found from the target channels
    
    4) A total number of {sna_total_messages} forwarded messages were found in the dataset'''

    print(analysis_results)

    # Save the analysis results to a text file
    with open('analysis-results.txt', 'w') as f:
        f.write(analysis_results)

def run_plotting(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)

    if 'Plotly' not in config:
        raise ValueError("Missing 'Plotly' section in the config file.")

    template = config['Plotly'].get('template')
    autosize = config['Plotly'].getboolean('autosize')
    width = config['Plotly'].getint('width')
    height = config['Plotly'].getint('height')

    df = pd.read_csv('master_messages.csv')
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M')
    messages_by_month = df.groupby(['channel_username', 'month']).size().reset_index(name='count')

    fig = go.Figure()
    for channel in messages_by_month['channel_username'].unique():
        channel_data = messages_by_month[messages_by_month['channel_username'] == channel]
        fig.add_trace(go.Scatter(
            x=channel_data['month'].astype(str),
            y=channel_data['count'],
            mode='lines',
            line_shape='spline',
            name=channel,
        ))

    fig.update_layout(
        title='Count of Messages per Month by Channel Username',
        template=template,
        autosize=autosize,
        width=width,
        height=height,
    )

    fig.write_image('messages_by_channel_by_month.png', engine='kaleido')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Social Network Analysis Script")
    parser.add_argument('--config', type=str, required=True, help='Path to the configuration file')
    parser.add_argument('--plot', action='store_true', help='Generate plot from the scraped data')

    args = parser.parse_args(['--config', 'config.ini'])

    if args.plot:
        run_plotting(args.config)
    else:
        nest_asyncio.apply()
        asyncio.run(main())
