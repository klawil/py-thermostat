#!/bin/bash

waitress-serve --port=80 --call 'app:create_app'
