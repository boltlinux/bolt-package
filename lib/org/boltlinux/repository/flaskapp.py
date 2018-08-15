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

from org.boltlinux.repository.flaskinit import app, api, db, app_init
from org.boltlinux.package.appconfig import AppConfig

###############################################################################
#
# App configuration
#
###############################################################################

config = AppConfig.instance().load_user_config()

app_config = config\
        .get("apps", {})\
        .get("repository", {})\
        .get("appconfig", {})

app_config.setdefault("SQLALCHEMY_DATABASE_URI",
        "sqlite:///" + AppConfig.get_config_folder() + os.sep +
            "repository.db")

app_init(app_config)

###############################################################################
#
# DB setup
#
###############################################################################

db.init_app(app)

with app.app_context():
    db.create_all()

###############################################################################
#
# API initialization
#
###############################################################################
import org.boltlinux.repository.api as api_v1

api.add_resource(api_v1.SourcePackage,
        "/v1/bolt/source",
        "/v1/bolt/source/<int:id_>")

