import os.path
import time
import file_grinder
start_time = time.time()

import config

def main():
	arms = config.get_arms_list()
	main_dir = config.get_main_dir()
	file_counter = 0
	bad_files = []
	for arm in arms:
		arm_data = file_grinder.read_dproj(arm["path"])
		for file in arm_data["modules"]+arm_data["forms"]:
			path = os.path.join(main_dir, arm["name"], file)
			try:
				file_grinder.grind(path)
			except file_grinder.SourceProcessingException as e:
				bad_files.append((arm["name"], path, e.function, e.message))
			except Exception as e:
				bad_files.append((arm["name"], path, e))
			file_counter+=1
	print("Проверено {} файлов за {} секунд".format(file_counter, (time.time() - start_time)))	
	print("Проблемные файлы")
	for f in bad_files:
		print(f)

if __name__ == "__main__":
	main()
