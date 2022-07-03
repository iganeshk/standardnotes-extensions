![Standard Notes Extension Repository](../assets/standardnotes.png?raw=true)

## Standard Notes Extensions - Self-Hosted Repository
Host Standard Notes extensions on your own server. This utility parses most of the open-source extensions available from the Standard Notes team as well as a range of extensions created by the wider Standard Notes community to build an extensions repository which can then be plugged directly into Standard Notes Web/Desktop Clients. (https://standardnotes.org/)

Extensions are listed as `YAML` in the `/extensions` sub-directory, pull a request if you'd like to add yours.

### Requirements
* Python 3
	* pyyaml module
	* requests module

### Demo
<p align="center">
	<img alt="Standard Notes Extension Repository Demo" src="https://github.com/iganeshk/standardnotes-extensions/raw/assets/standardnotes_demo.gif" width="80%" />
</p>

### Usage

* Clone this repository to your web-server:
```bash
$ git clone https://github.com/iganeshk/standardnotes-extensions.git
$ cd standardnotes-extensions
$ pip3 install -r requirements.txt
```
* Visit the following link to generate a personal access token:
```
$ https://github.com/settings/tokens
```
![Github Personal Access Token](../assets/github_personal_token.png?raw=true)

* Use the provided [`env.sample`](../env.sample) to create a `.env` file for your environment variables and including your Github personal access token.

```
# Sample ENV setup Variables (YAML)
# Copy this file and update as needed.
#
#   $ cp env.sample .env
#
# Do not include this new file in source control
# Github Credentials
# Generate your token here: https://github.com/settings/tokens
# No additional permission required, this is just to avoid github api rate limits
#

domain: https://your-domain.com/extensions

github:
  username: USERNAME
  token: TOKEN

```

* [Optional] Add more extensions to the `/extensions` directory, using the `YAML` sample templates for [extensions](../extension.yaml.sample) or [themes](../theme.yaml.sample), or modify any existing extensions.
* Run the utility:

```bash
$ python3 build_repo.py
```
* Serve the `/public` directory and verify that the endpoint is reachable.

```
https://your-domain.com/extensions/index.json
```
* Import the `latest url` for each extension you want to add (for example: `https://your-domaim.com/extensions/bold-editor/index.json`) into the Standard Notes Web Desktop client under the `General` > `Advanced Settings` > `Install Custom Extension` menu. (Note: Enable CORS for your web server respectively, nginx setup provided below)

* If you are self-hosting Standard Notes Server (aka [Standard Notes Standalone](https://github.com/standardnotes/standalone)), you may need to add a "subscription" to your self-hosted user account in order to avoid any problems accessing official Standard Notes extensions. 
* To add a subscription to your self-hosted user account, run the following commands (Replace EMAIL@ADDR with your user email) from within your standalone directory:
`./server.sh create-subscription EMAIL@ADDR`

### Docker

* To run via Docker, clone this repository, create your `.env` file using the provided `env.sample`, and optionally add any additional extensions to the `/extensions` directory, following the instructions above.
* Then pull and run the container, specifying the mount points for the `.env` file, the `extensions` directory, and the `public` directory, where the self-hosted extensions will be placed:

```bash
$ docker run \
  -v $PWD/.env:/build/.env \
  -v $PWD/extensions:/build/extensions \
  -v $PWD/public:/build/public \
  -v $PWD/standardnotes-extensions-list.txt:/build/standardnotes-extensions-list.txt \
  iganesh/standardnotes-extensions
```

#### Docker Compose

If you would like to use the container with docker-compose, the exact setup will be somewhat specific to your configuration, however the following snippet may be helpful, assuming you have cloned this repository in your `$HOME` directory and followed the instructions regarding the `.env` file and `/extensions` directory:

```yaml
version: '3.3'
services:
  nginx:
  ...
    volumes:
    - standardnotes-extensions:/usr/share/nginx/html

  standardnotes-extensions:
    image: iganesh/standardnotes-extensions
    restart: "no"
    volumes:
      - $HOME/standardnotes-extensions/.env:/build/.env
      - $HOME/standardnotes-extensions/extensions:/build/extensions
      - $HOME/standardnotes-extensions/standardnotes-extensions-list.txt:/build/standardnotes-extensions-list.txt
      - standardnotes-extensions:/build/public

volumes:
  standardnotes-extensions:
    name: standardnotes-extensions
```

This snippet will handle the building of the extension creation-container, and place the result in the `standardnotes-extensions` volume, which can then be mounted in the nginx container so that it can be served as demonstrated in the instructions below. Note that it's necessary to include the `restart: "no"` flag, because the container is designed to stop after it has finished generating the extensions.

Also, please note that the configuration snippet above is in no way a complete setup: you will still have to configure the nginx container and set up the syncing server containers.

### Docker Build

If you need to build the container, clone this repository, `cd` into it, and run the following command:

```bash
$ docker build --no-cache -t standardnotes-extensions:local .
```

### Setup with nginx

```nginx
	location ^~ /extensions {
		autoindex off;
		alias /path/to/standardnotes-extensions/public;
		# CORS HEADERS
		if ($request_method = 'OPTIONS') {
		   add_header 'Access-Control-Allow-Origin' '*';
		   add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
		   #
		   # Custom headers and headers various browsers *should* be OK with but aren't
		   #
		   add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-Application-Version,X-SNJS-Version';
		   #
		   # Tell client that this pre-flight info is valid for 20 days
		   #
		   add_header 'Access-Control-Max-Age' 1728000;
		   add_header 'Content-Type' 'text/plain; charset=utf-8';
		   add_header 'Content-Length' 0;
		   return 204;
		}
		if ($request_method = 'POST') {
		   add_header 'Access-Control-Allow-Origin' '*';
		   add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
		   add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-Application-Version,X-SNJS-Version';
		   add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
		}
		if ($request_method = 'GET') {
		   add_header 'Access-Control-Allow-Origin' '*';
		   add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
		   add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-Application-Version,X-SNJS-Version';
		   add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
		}
	}
```

### Acknowledgments
* This project was adapted originally from https://github.com/JokerQyou/snextensions
* Check out https://github.com/jonhadfield/awesome-standard-notes for more Standard Notes stuff!
* Authors of custom themes and extensions
