def custom_print(sys_message):
    with open('app_logs.txt', 'a', encoding='utf8') as logs:
        print(sys_message, file=logs)