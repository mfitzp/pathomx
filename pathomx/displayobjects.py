

class BaseObj(object):

    def __unicode__(self):
        return self.text

    def __init__(self, text, **kwargs):
        self.text = text


class Svg(BaseObj):
    pass


class Html(BaseObj):
    pass
