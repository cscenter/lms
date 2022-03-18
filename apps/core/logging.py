import logging

from pythonjsonlogger.jsonlogger import JsonFormatter as BaseFormatter


class JsonFormatter(BaseFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname


class SQLFormatter(logging.Formatter):
    """
    In case you’re working with a 256 color terminal, you should use
    the Terminal256Formatter instead of the TerminalTrueColorFormatter.
    """

    def format(self, record):
        # Check if Pygments is available for coloring
        try:
            import pygments
            from pygments.formatters import TerminalTrueColorFormatter
            from pygments.lexers import SqlLexer
        except ImportError:
            pygments = None

        # Check if sqlparse is available for indentation
        try:
            import sqlparse
        except ImportError:
            sqlparse = None

        # Remove leading and trailing whitespaces
        sql = record.sql.strip()

        if sqlparse:
            # Indent the SQL query
            sql = sqlparse.format(sql, reindent=True)

        if pygments:
            # Highlight the SQL query
            sql = pygments.highlight(
                sql,
                SqlLexer(),
                TerminalTrueColorFormatter(style='monokai')
            )

        # Set the record's statement to the formatted query
        record.statement = sql
        return super(SQLFormatter, self).format(record)
