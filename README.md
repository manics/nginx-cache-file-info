# Extract metadata from Nginx cache

Python script to displays Nginx cache metadata such as creation and validity times for cached files such as those created by [`proxy_cache`](http://wiki.nginx.org/HttpProxyModule#proxy_cache).


## Usage

    ./nginx_cache_file_info.py files ...

E.g.:

    ./nginx_cache_file_info.py /var/cache/nginx/a/bc/*


## Change expiry date

Nginx cache files include the expiry time, so if the configured Nginx cache expiry time is reduced old files may still be returned.
Use `--set-date ISO-DATE-TIME` to change the expiry time, e.g.:

    ./nginx_cache_file_info.py c3681f3e515f4b83bbc9672fca3e9929-new --set-expire 2019-02-21T12:00:00


## About

See [`nginx_cache_file_info.py`](nginx_cache_file_info.py) for the technical details of how Nginx cache files are stored.

This script has been tested on Nginx running on Linux x86_64 (CentOS 7, Linux x86_64 nginx-1.14.2-1.el7_4.ngx.x86_64) and invovled some trial and error.
It may require adjustment to work on other platforms.

This script was inspired by: https://github.com/perusio/nginx-cache-inspector
