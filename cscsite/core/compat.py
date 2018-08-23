from bitfield import BitHandler
from bitfield.forms import BitFieldCheckboxSelectMultiple


class Django21BitFieldCheckboxSelectMultiple(BitFieldCheckboxSelectMultiple):
    """
    Django 2.1 compatible version. django-bitfield 1.9.3 affected by error

    TypeError: render() got an unexpected keyword argument 'renderer'
    """
    def render(self, name, value, attrs=None, choices=(), renderer=None):
        if isinstance(value, BitHandler):
            value = [k for k, v in value if v]
        elif isinstance(value, int):
            real_value = []
            div = 2
            for (k, v) in self.choices:
                if value % div != 0:
                    real_value.append(k)
                    value -= (value % div)
                div *= 2
            value = real_value
        return super(BitFieldCheckboxSelectMultiple, self).render(
            name, value, attrs=attrs, renderer=renderer)
