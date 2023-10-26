# Twitch OpenAI IRC Bot

The "psi_mathison" bot, designed to enhance the experience of watching StarCraft II (SC2) streams, utilizes a combination of technologies, including the Twitch chat interface, OpenAI's GPT models, and the SC2 client for real-time integration. Through monitoring the game states, the bot dynamically interacts with the Twitch chat associated with the stream, responding to user queries, commenting on gameplay, and adding customized engagement through Mood and Perspective settings. 

It incorporates various features such as control over message sending, extensive logging, game state monitoring, and more. By providing analytical insights, humor, or other emotive responses, "psi_mathison" brings a unique and lively dimension to the SC2 viewing experience.

If you have any questions reach out to me at:

https://twitter.com/karljayg  Same tag on instagram, or email me at kj (at) psistorm.com

See its use in one of our recent broadcasts: https://www.youtube.com/watch?v=gyRU2YE14uU

Additional documentation: https://docs.google.com/document/d/1C8MM_BqbOYL9W0N0qu0T1g2DS7Uj_a6Vebd6LJLX4yU/edit?usp=sharing

## Getting Started

### Prerequisites

Before you can use this bot, you will need to:

- Obtain a Twitch account
- Obtain an OAuth token for your Twitch account from https://twitchapps.com/tmi/
- Obtain an OpenAI API key

### Installing

1. Clone this repository to your local machine
2. Install the required Python packages by running:
```
pip install -r requirements.txt
```
   or manually:
```
pip install irc openai logging requests re asyncio random irc.bot spacy nltk en_core_web_sm logging urllib3
python -m spacy download en_core_web_sm
```

3. Set up the configuration file by copying `settings.example.py` to `settings.py` and replacing the placeholders with your own values

### Usage

Initilize DB migration

```
cd setup
```
```
python setup.py
```


To start the bot, run in your terminal:

```
python app.py
```

In your Twitch channel chat, type "open sesame" followed by your message to generate a response from the OpenAI API.

### Setup Instructions for llama-chat-hf.ipynb

Follow these steps to set up your environment to run the `llama-chat-hf.ipynb` notebook:

1. **Install Jupyter Notebook**: If you haven't already, install Jupyter Notebook, which is required to run the Jupyter notebook.

    ```shell
    pip install notebook
    ```

2. **Install Transformers Library**: Install the Transformers library, which is developed by Hugging Face and is used for natural language processing tasks.

    ```shell
    pip install transformers
    ```

3. **Create an Access Token from Hugging Face**: Go to the Hugging Face website (https://huggingface.co/) and create an account if you don't have one. Once you're logged in, you can generate an API token by going to your profile settings. This token is used to access Hugging Face models and datasets.

4. **Install PyTorch**: PyTorch is a deep learning framework that is often used in conjunction with the Transformers library. You can install PyTorch by following the installation instructions on the PyTorch website: [PyTorch Installation](https://pytorch.org/). For example, if you want to install it with CUDA support, you can use the following command:

    ```shell
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    ```

    Be sure to choose the appropriate version based on your system and requirements.

5. **Install Accelerate**: Accelerate is a library for PyTorch and Transformers that simplifies distributed training. You can install it as follows:

    ```shell
    pip install accelerate
    ```

6. **Enable Developer Mode for `symlink` (optional)**: If you're specifically instructed to enable developer mode for `symlink`, you should follow the relevant instructions for your operating system. Typically, this involves enabling developer mode through system settings.

7. **Run Jupyter Notebook**: Open a terminal and navigate to the directory where `llama-chat-hf.ipynb` is located. Then, run the following command to start Jupyter Notebook:

    ```shell
    jupyter notebook
    ```

   This will open the Jupyter Notebook interface in your web browser. From there, you can open the `llama-chat-hf.ipynb` notebook and execute the provided code.

Make sure to open the notebook in Jupyter Notebook, load the provided Python code, and set the appropriate paths and API tokens as instructed in the notebook itself.


## License


# chan notes(to be removed once done):
   - https://www.youtube.com/watch?v=25P5apB4XWM - 

   - https://www.youtube.com/watch?v=e9yMYdnSlUA - organized python codes
      
   - https://www.youtube.com/watch?v=rp1QR3eGI1k - refactoring tips

   - https://www.youtube.com/watch?v=8rynRTOr4mE -  state management


### project package/module file structuring
twitch-gpt-chat-bot
    ┣ api
    ┃   ┣ aligulac.py
    ┃   ┗ twitch_bot.py
    ┣ logs
    ┣ models
    ┃   ┣ game_info.py
    ┃   ┣ log_once_within_interval_filter.py
    ┃   ┗ mathison_db.py
    ┣ settings
    ┃   ┣ config.example.py
    ┃   ┣ config.py
    ┃   ┣ SC2_sounds.example.json
    ┃   ┗ SC2_sounds.json
    ┣ setup
    ┃   ┗ setup.sql
    ┣ sound
    ┣ temp
    ┣ test
    ┃   ┗ replays
    ┃   ┗ SC2_game_result_test.json
    ┣ utils
    ┃   ┣ file_utils.py
    ┃   ┣ load_replays.py
    ┃   ┣ sc2replaystats.py
    ┃   ┣ tokensArray.py
    ┃   ┗ wiki_utils.py
    ┣ .gitignore
    ┣ app.py
    ┣ LICENSE.md
    ┣ README.md
    ┣ requirements.txt
    