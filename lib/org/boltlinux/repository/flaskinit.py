# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2018 Tobias Koch <tobias.koch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import os
import base64

from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

extra_vars = [
    "FLASK_STATIC_URL_PATH",
    "FLASK_STATIC_FOLDER",
    "FLASK_ROOT_PATH"
]

extra_args = {}

for var in extra_vars:
    if var in os.environ:
        argname = var.lower().split("_", 1)[-1]
        extra_args[argname] = os.environ[var]
    #end if
#end for

app = Flask(__name__, **extra_args)
api = Api(app)
db  = SQLAlchemy()

def app_init(config):
    settings = {
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "ERROR_404_HELP":  False
    }

    settings.update(config)
    secret_key = settings.get("SECRET_KEY", None)

    if isinstance(secret_key, str):
        try:
            settings["SECRET_KEY"] = \
                    base64.decodestring(secret_key.encode("utf-8"))
        except Exception:
            pass
    else:
        settings["SECRET_KEY"] = os.urandom(32)

    app.config.update(settings)
#end function

