#!/bin/sh

set -euf

if [ -z "${TERM-}" ]; then
    echo 'no TERM var, assuming sane default'
    tput='tput -T xterm-256color'
else
    tput='tput'
fi

red=$($tput setaf 1)
green=$($tput setaf 2)
blue=$($tput setaf 4)
white=$($tput setaf 7)
bold=$($tput bold)
reset=$($tput sgr0)

info() {
    echo "${bold}${white}━━┫${blue}${@}${white}┣━━${reset}"
}

success() {
    echo "${bold}${white}━━┫${green}${@}${white}┣━━${reset}"
}

warn() {
    echo "${bold}${red}!! ${white}${@}${reset}"
}

if ! [[ -n "${VIRTUAL_ENV+set}" ]]
then
    warn "Please run this script with poetry run ./style or from within a poetry shell"
    exit
fi

info "black"
black .

info "isort"
isort .

info "xenon"
xenon --no-assert -a A -m B -b B .

info "ruff"
ruff metis tests wsgi.py

info "refurb"
refurb metis tests wsgi.py

success "all checks completed."
