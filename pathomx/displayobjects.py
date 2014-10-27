import os
from copy import copy
from . import utils
from IPython.nbconvert.filters.markdown import markdown2html_mistune

css = os.path.join(utils.scriptdir, 'html', 'css', 'style.css')


class BaseObj(object):

    def __unicode__(self):
        return self.data

    def __init__(self, data, **kwargs):
        self.data = copy(data)


class Svg(BaseObj):
    pass


class Html(BaseObj):

    def __init__(self, data, **kwargs):

        if type(data) == str or type(data) == unicode:
            html_data = data

        # Support IPython notebook aware objects
        elif hasattr(data, '_repr_html_'):
            html_data = data._repr_html_()

        if '<html' in html_data:
            self.data = html_data
        else:
            # Incomplete HTML wrap with the default CSS
            self.data = '''<html>
<head><title>About</title><link rel="stylesheet" href="{css}"></head>
<body>
<div class="container" id="notebook-container">
<div class="cell border-box-sizing text_cell rendered">
<div class="inner_cell">
<div class="text_cell_render border-box-sizing rendered_html">{html}</div>
</div>
</div>
</div>
</div>
        </body>
        </html>'''.format(**{'baseurl': 'file://' + os.path.join(utils.scriptdir), 'css': 'file://' + css, 'html': html_data})


class Markdown(Html):

    def __init__(self, data, **kwargs):
        super(Markdown, self).__init__(markdown2html_mistune(data))
