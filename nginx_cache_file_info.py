#!/usr/bin/env python

from __future__ import print_function
import struct
from argparse import ArgumentParser
from collections import namedtuple
from datetime import datetime
import sys
import time


def parse_date_string(s):
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError('Unable to parse date: {}'.format(s))


def string_or_none(bytes):
    if set(bytes) == {0}:
        return None
    return bytes.decode('ascii')


def datetime_or_none(timet):
    timet_max = 2**64 - 1
    if timet == timet_max:
        return None
    return datetime.fromtimestamp(timet)


# https://github.com/nginx/nginx/blob/release-1.14.2/src/http/ngx_http_cache.h#L26-L28
# # define NGX_HTTP_CACHE_KEY_LEN       16
# # define NGX_HTTP_CACHE_ETAG_LEN      128
# # define NGX_HTTP_CACHE_VARY_LEN 128

# https://github.com/nginx/nginx/blob/release-1.14.2/src/http/ngx_http_cache.h#L126-L142
# typedef struct {
#     ngx_uint_t                       version;
#     time_t                           valid_sec;
#     time_t                           updating_sec;
#     time_t                           error_sec;
#     time_t                           last_modified;
#     time_t                           date;
#     uint32_t                         crc32;
#     u_short                          valid_msec;
#     u_short                          header_start;
#     u_short                          body_start;
#     u_char                           etag_len;
#     u_char                           etag[NGX_HTTP_CACHE_ETAG_LEN];
#     u_char                           vary_len;
#     u_char                           vary[NGX_HTTP_CACHE_VARY_LEN];
#     u_char                           variant[NGX_HTTP_CACHE_KEY_LEN];
# } ngx_http_file_cache_header_t;

NGINX_CACHE_HEADER_SIZE = 336

NginxCacheHeader = namedtuple('NginxCacheHeader', (
    'version',
    'valid_sec',
    'updating_sec',
    'error_sec',
    'last_modified',
    'date',
    'crc32',
    'valid_msec',
    'header_start',
    'body_start',
    'etag_len',
    'etag',
    'vary_len',
    'vary',
    'variant'))


def parse_nginx_cache_file(cache_file):
    with open(cache_file, 'rb') as f:
        d = f.read()

    header = d[:NGINX_CACHE_HEADER_SIZE]

    # https://docs.python.org/3.6/library/struct.html
    # Sizes are for Linux x86_64 nginx-1.14.2-1.el7_4.ngx.x86_64
    #            88888842221    128  1    128   16
    formats = ('<QQQQQQIHHHB', 'c', 'B', 'c',  'c',)

    fields = ['None'] * 15

    # version valid_sec updating_sec error_sec last_modified date crc32
    # valid_msec header_start body_start etag_len
    fields[:11] = list(struct.unpack_from(formats[0], header))
    offset = struct.calcsize(formats[0])

    if fields[0] != 5:
        raise Exception('Unexpected version: {}'.format(fields[0]))

    fields[1] = datetime_or_none(fields[1])
    fields[4] = datetime_or_none(fields[4])
    fields[5] = datetime_or_none(fields[5])

    # etag
    fields[11] = string_or_none(header[offset:(offset + 128)])
    offset += 128

    # vary_len
    fields[12] = struct.unpack_from(formats[2], header)[0]
    offset += struct.calcsize(formats[2])

    # vary
    fields[13] = string_or_none(header[offset:(offset + 128)])
    offset += 128

    # variant
    fields[14] = string_or_none(header[offset:(offset + 16)])
    offset += 16

    # Is there always 4 bytes of 0 padding?
    assert NGINX_CACHE_HEADER_SIZE - offset == 4
    extra = d[offset:NGINX_CACHE_HEADER_SIZE]
    #            Python3               Python2
    if set(extra) != {0} and set(extra) != {'\x00'}:
        print('Unexpected non-zero bytes: {}'.format(extra), file=sys.stderr)

    hdr = NginxCacheHeader(*fields)
    # Not sure if the cache KEY has to be ascii
    key = d[NGINX_CACHE_HEADER_SIZE:hdr.header_start].decode('ascii')
    assert key[:6] == '\nKEY: '
    assert key[-1] == '\n'
    key = key[6:-1]
    http_header = d[hdr.header_start:hdr.body_start].decode('ascii')
    http_body = d[hdr.body_start:]

    return hdr, key, http_header, http_body


def set_expire_nginx_cache_file(cache_file, expiredt):
    valid_sec = int(time.mktime(expiredt.timetuple()))
    with open(cache_file, 'r+b') as f:
        f.seek(8)
        f.write(struct.pack('<Q', valid_sec))


def main():
    parser = ArgumentParser(description='Examine Nginx cache file')
    parser.add_argument(
        '--set-expire', help='Modify expiry date (valid_sec) in cache files')
    parser.add_argument('files', nargs='+', help='Nginx cache files')
    parser.add_argument(
        '-q', '--quiet', action='store_true', help='Hide output')
    args = parser.parse_args()

    set_expire = None
    for cache_file in args.files:

        hdr, key, http_header, http_body = parse_nginx_cache_file(
            cache_file)

        if args.set_expire:
            set_expire = parse_date_string(args.set_expire)
            set_expire_nginx_cache_file(cache_file, set_expire)

        if not args.quiet:
            print('** Nginx cache header ** {}'.format(cache_file))
            for k, v in hdr._asdict().items():
                print('{}: {}'.format(k, v))

            print('\n** Nginx cache key **\n{}'.format(key))
            print('\n** HTTP headers **\n{}'.format(http_header.strip()))
            print('\n** HTTP body length **\n{}'.format(len(http_body)))


if __name__ == '__main__':
    main()
