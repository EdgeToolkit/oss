#!/usr/bin/env bash
_DIR=$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)
_TOP=$(cd $_DIR/../.. && pwd)
_DB=$_TOP/.ansible/config/tokens.yml

_REGISTRATION_TOKEN=
_PRIVATE_TOKEN=kypLygrDSZ-92NewWx4R
_GITLAB_URL=http://172.16.0.121:8200
cd $_TOP

function ci() {
  python $_DIR/ci.py --url $_GITLAB_URL --token $_PRIVATE_TOKEN --db $_DB $*
}


function _reset() {
  ci reset *
}

