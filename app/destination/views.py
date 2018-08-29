from . import dest_bp
from ..models import Destination
from flask import (
    abort,
    render_template,
)


@dest_bp.route('/destinations/<slug>')
def page(slug):
    destination = Destination.find_by_slug(slug)

    if not destination:
        destination = Destination.first_by_uuid(slug)

    if not destination:
        abort(404)

    return render_template(
        'destinations/show.html',
        destination=destination,
    )
