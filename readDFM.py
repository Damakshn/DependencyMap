def delete_word_wraps_in_sql(source):
	"""
	Удаляет кривые переносы строк, которые рисует Delphi в поле SQL своих компонентов.
	"""
	pattern = b"' +\r\n"
	word_wrap_position = source.find(pattern)
	while word_wrap_position >= 0:
		quote_position = source[word_wrap_position+1:].find(b"'")		
		source = source[:word_wrap_position]+source[word_wrap_position+quote_position+2:]
		word_wrap_position = source.find(pattern)
	return source


def decode_sharps(source):
	"""
	Исправляет перекодированные Delphi русские буквы.
	Delphi заменяет кириллические символы на #<код в utf-8>.
	"""
	digits = {ord(str(d)) for d in range(10)}
	sharp_position = source.find(b"#")
	while sharp_position >= 0:
		code_length = 1
		while source[sharp_position+code_length+1] in digits:
			code_length += 1
		char_to_insert = bytes(chr(int(source[sharp_position+1:sharp_position+code_length+1])), "utf-8")
		source = source[:sharp_position]+char_to_insert+source[sharp_position+code_length+1:]		
		sharp_position = source.find(b"#")
	return source

def delete_blank_lines(source):
	whitespaces = (" ", "\t", "\0")
	prev_pos = -1
	end_of_line = 0
	current_pos = source.find(b"\r\n")	
	while current_pos >= 0:		
		if prev_pos == -1:
			prev_pos = current_pos
			current_pos = source.find(b"\r\n", current_pos+1)
			continue		
		line = source[prev_pos+2:current_pos]
		line_is_blank = True
		char = 0		
		while line_is_blank and char < len(line):		
			if not (chr(line[char]) in whitespaces):				
				print("~"+chr(line[char])+"~")
				line_is_blank = False
			char += 1
		if line_is_blank:			
			source = source[:prev_pos]+source[current_pos:]
		prev_pos = current_pos
		current_pos = source.find(b"\r\n", current_pos+1)				
	return source

def delete_commented_code(source, comment_pattern):
	comment_open, comment_close, inline_comment = comment_pattern	
	comment_start = source.find(comment_open)
	while comment_start >= 0:
		comment_end = source.find(comment_close, comment_start+2)
		if comment_end >= 0:
			source = source[:comment_start]+source[comment_end+2]
		else:
			source = source[:comment_start]
		comment_start = source.find(comment_open, comment_start+2)

	comment_start = source.find(inline_comment)
	while comment_start >= 0:
		comment_end = source.find(b"\r\n", comment_start+2)
		source = source[:comment_start]+source_code[comment_end:]
		comment_start = source.find(inline_comment, comment_end)
	return source

def delete_sql_comments(source):
	sql_comment_pattern = (b"/*", b"*/", b"--")
	return delete_commented_code(source, sql_comment_pattern)

def delete_pascal_comments(source):
	pascal_comment_pattern = (b"{", b"}", b"//")
	return delete_commented_code(source, pascal_comment_pattern)

def delete_passive_code(source):
	return source

def save_this_shit(path, source):
	f = open('draft.txt', 'wb')
	f.write(source)
	f.close()

def compress_dephi_form_file(path, source):
	source = open(path, "rb").read()
	source = delete_word_wraps_in_sql(source)
	source = decode_sharps(source)
	source = delete_blank_lines(source)
	save_this_shit(path, source)

def compress_dephi_source_file(path, source):
	source = open(path, "rb").read()
	no_sharps = decode_sharps(source)
	no_sharps_no_comments = delete_pascal_comments(no_sharps)
	no_sharps_no_comments_no_blank_lines = delete_blank_lines(no_sharps_no_comments)
	save_this_shit(path, no_sharps_no_comments_no_blank_lines)
