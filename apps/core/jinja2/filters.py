from core.utils import render_markdown_and_cache, get_youtube_video_id


def markdown(value, fragment_name, expires_in=0, *vary_on):
    return render_markdown_and_cache(value, fragment_name, expires_in, *vary_on)


def pluralize(number, singular, genitive_singular, genitive_plural):
    """Plurals with numbers"""
    endings = [singular, genitive_singular, genitive_plural]
    if number % 100 in (11, 12, 13, 14):
        return endings[2]
    if number % 10 == 1:
        return endings[0]
    if number % 10 in (2, 3, 4):
        return endings[1]
    else:
        return endings[2]


def with_classes(bound_field, class_names):
    """Render field with additional classes"""
    css_classes = bound_field.field.widget.attrs.get('class', '')
    if css_classes:
        css_classes = css_classes.split(' ')
    else:
        css_classes = []
    for class_name in class_names.strip().split(' '):
        if class_name not in css_classes:
            css_classes.append(class_name)
    widget_str = bound_field.as_widget(attrs={'class': ' '.join(css_classes)})
    if bound_field.field.show_hidden_initial:
        return widget_str + bound_field.as_hidden(only_initial=True)
    return widget_str


def youtube_video_id(url):
    return get_youtube_video_id(url)
