"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
class LogRouter:
    """
    A router to control all database operations on models for the logger.

    """
    route_app_labels = {'log_ext'}

    def db_for_read(self, model, **hints):
        """
        Attempts to read log models go to log_db.
        
        """
        if model._meta.app_label in self.route_app_labels:
            return 'log_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write log models go to log_db.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'log_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the log app is involved.
        """
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the the 'log_db' database consists of the log app and nothing
        else.

        """
        if app_label in self.route_app_labels:
            return db == 'log_db'
        # Redirect all other app labels to default database
        return db == 'default'
