<img alt="LaMetric-System-Monitor" src="https://standardnotes.org/assets/icon.png"/>

## Standard Notes Extensions - Self-Hosted Repository
Host Standard Notes extensions on your own server. This utility parses list of extensions configured in YAML from the `\extensions` directory, builds a repository JSON index which can be plugged directly into Standard Notes Web/Desktop Clients. (https://standardnotes.org/)

### Requirements
* Python 3
* Python 3 - pyyaml module

### Usage

* Fork this repository to the web-server:

```bash
$ git clone https://github.com/iganeshk/standardnotes-extensions.git
$ cd standardnotes-extensions
$ pip3 install -r requirements.txt
```

* Replace `your-domain.com` at the end of the `build-repo.py` file with your domain name:

```
main(os.getenv('URL', 'https://your-domain.com/extensions'))
```

* [Optional] Make additions or appropriate changes in `/extensions` directory
* Run the utility:

```bash
$ python3 build-repo.py
```
* Server the `/public` directory and verify if the endpoint is reachable

```
https://your-domain.com/extensions/index.json
```
* Import the above endpoint into the web/desktop client.

### Setup with nginx as reverse-proxy

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
		   add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range';
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
		   add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range';
		   add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
		}
		if ($request_method = 'GET') {
		   add_header 'Access-Control-Allow-Origin' '*';
		   add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
		   add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range';
		   add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
		}
	}
```

### Acknowledgments
This project was adapted from https://github.com/JokerQyou/snextensions to facilitate on-the-fly updating of extensions.

### ToDo
* Implement the usage of GitHub API for efficiency.