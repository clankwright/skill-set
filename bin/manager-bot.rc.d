#!/bin/sh
#
# PROVIDE: manager_bot
# REQUIRE: NETWORKING
# KEYWORD: shutdown
#
# Add to /etc/rc.conf to enable:
#   manager_bot_enable="YES"
#   manager_bot_user="<username>"
#   manager_bot_dir="/path/to/skill-set"
#   manager_bot_env_file="/path/to/.config/manager-telegram.env"

. /etc/rc.subr

name="manager_bot"
rcvar="${name}_enable"
load_rc_config $name

: ${manager_bot_enable:="NO"}
: ${manager_bot_user:="nobody"}
: ${manager_bot_dir:="/path/to/skill-set"}
: ${manager_bot_env_file:="/path/to/.config/manager-telegram.env"}
: ${manager_bot_log:="/var/log/manager_bot.log"}
: ${manager_bot_python:="/usr/local/bin/python3.11"}

pidfile="/var/run/${name}.pid"
command="/usr/sbin/daemon"
command_args="-r -R 10 -P ${pidfile} \
    -o ${manager_bot_log} \
    /usr/bin/env TELEGRAM_ENV_FILE=${manager_bot_env_file} \
    ${manager_bot_python} ${manager_bot_dir}/bin/manager-bot.py"

start_precmd="${name}_precmd"

manager_bot_precmd() {
    install -o ${manager_bot_user} -g ${manager_bot_user} -m 640 \
        /dev/null ${manager_bot_log}
    install -o ${manager_bot_user} -g ${manager_bot_user} -m 644 \
        /dev/null ${pidfile}
}

run_rc_command "$1"
