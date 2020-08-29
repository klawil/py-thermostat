#!/bin/bash

sudo waitress-serve --port=80 --call 'app:create_app'
