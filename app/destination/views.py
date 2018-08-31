from . import dest_bp
from ..models import Destination
from flask import (
    abort,
    render_template,
)


@dest_bp.route('/destinations/<uuid>')
def page(uuid):
    destination = Destination.first_by_uuid(uuid)

    if not destination:
        abort(404)

    return render_template(
        'destinations/show.html',
        destination=destination,
    )
