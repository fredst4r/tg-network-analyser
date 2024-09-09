# Telegram Network Analysis

This script analyzes message data from a target channel(s), outputs a list of channels that have content forwarded by the target channel(s) and plots the number of messages by channel by month

## Prerequisites

- Python >3.9
- telethon
- pandas
- tqdm
- asyncio
- nest_asyncio
- csv
- re
- configparser
- plotly

## Installation

Clone the repository or download the script:

```
    git clone https://github.com/fr3dst4r/telegram-network-analysis.git
```
    
Install the required Python packages from the requirements.txt file using pip:

```
    pip install -r requirements.txt
```

## Usage

Ensure you populate the config.ini file with your Telegram credentials and target channel usernames (api_key, api_hash, phone, username, channel_username). For example:

```
    api_key = [YOUR_API_KEY]
    api_hash = [YOUR_HAS_KEY]
    phone = [YOUR_PHONE_NUMBER]
    username = [YOUR_USERNAME]
    channel_usernames = [TARGET_CHANNEL_USERNAME]*
```

*Target channel usernames must be split with a comma, for example: target1,target2,target3

It is optional, but you can populate the Plotly section of the config.ini file with a customised template, autosize, width, and height. To see the documentation for this, go to Plotly's documentation on line and scatter plots at https://plotly.com/python/line-and-scatter/

Running the Script:

For Linux/MacOS:
```
./your_script_name.py --config path/to/config.ini
```
For Windows:
```
python your_script_name.py --config path\to\config.ini
```

Windows users can also run the ```run_analysis.bat``` file if they prefer

To generate the plot:
```
./your_script_name.py --config path/to/config.ini --plot
```

## Data Output

The output comes in three formats. The first is the 'master-messages.csv' file, which contains all scraped messages from all channels:

![Example CSV](https://github.com/tgsn-co/tg-analysis/blob/readme-images/Screenshot%202024-09-02%20at%2014.27.25.png)

The second is another CSV file called 'analysis-results.csv', which contains a list of all channels that have had content forwarded by the target channel(s):

![Example CSV](https://github.com/tgsn-co/tg-analysis/blob/readme-images/Screenshot%202024-09-02%20at%2016.13.35.png)

The third is a text output that's saved as a text file that includes basic statistics of the process, such as:
```
Social network analysis completed successfully!

    Here are the results:

    1) A total of 2 target channels were scraped for messages

    2) A total of 10080 messages were scraped from the target channels

    3) A total number of 768 forwarded channels were found from the target channels
    
    4) A total number of 4748 forwarded messages were found in the dataset
```

## Visual Output

An example of the expected plot is as follows:

![Example Plot](https://github.com/tgsn-co/tg-analysis/blob/readme-images/rim-impersky.png)

## Telegram Specifics

A few words on using Telegram and Telethon. Firstly, as an OSINT professional, use the script alongside a sock puppet Telegram account to ensure operational security. Secondly, with Telethon, as you're making API requests to Telegram, there are rate limits. This can sometimes lead to the following error code:

```
    telethon.errors.rpcerrorlist.FloodWaitError: A wait of [NUMBER_OF_SECONDS] seconds is required (caused by [TYPE_OF_REQUEST)
```

Unfortunately, there is nothing that can be done about this. Finally, not all forwarded_from channels can be accessed as they are private, which can generate the following error code:

```
    telethon.errors.rpcerrorlist.ChannelPrivateError: The channel specified is private and you lack permission to access it. Another reason may be that you were banned from it.
```

Like the second point, unfortunately, there is nothing that can be done about this. A list of all error codes is available on the Telethon documentation at https://tl.telethon.dev/methods/channels/get_full_channel.html

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
