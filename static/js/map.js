function initMap() {
    var us = {lat: 37.1, lng: -95.7};
    var countryRestrict = {'country': 'us'};

    // Namespaced globals. :(
    carpool_starting_markers = [];
    carpool_ending_markers= [];

    carpool_map = new google.maps.Map(document.getElementById('map'), {
        zoom: 4,
        center: us,
        mapTypeControl: false,
        streetViewControl: false
    });

    autocompleteFromInput = new google.maps.places.Autocomplete(
        document.getElementById('leaving_from'),
        {
            types: ['geocode'],
            componentRestrictions: countryRestrict
        }
    );

    autocompleteToInput = new google.maps.places.Autocomplete(
        document.getElementById('going_to'),
        {
            types: ['geocode'],
            componentRestrictions: countryRestrict
        }
    );

    autocompleteFromInput.addListener('place_changed', autocompleteFromHandler);
    autocompleteToInput.addListener('place_changed', autocompleteToHandler);

    loadMarkers(carpool_starting_locations, carpool_map, 'starting', false);
    loadMarkers(carpool_ending_locations, carpool_map, 'ending', true);
}

function autocompleteFromHandler() {
    var place = autocompleteFromInput.getPlace();
    var location = place.geometry.location;
    panMap(location, carpool_map);
    addMarker(location, carpool_map);
    document.getElementById('from_latitude').value = location.lat();
    document.getElementById('from_longitude').value = location.lng();
}

function autocompleteToHandler() {
    var place = autocompleteToInput.getPlace();
    var location = place.geometry.location;
    panMap(location, carpool_map);
    addMarker(location, carpool_map);
    document.getElementById('to_latitude').value = location.lat();
    document.getElementById('to_longitude').value = location.lng();
}

function panMap(location, map) {
    map.setCenter(location);
    map.setZoom(6);
}

function addMarker(location, map, type) {
    var marker = new google.maps.Marker({
        position: location,
        map: map
    });
    if (type === 'starting' || type === 'ending') {
        marker.addListener('click', function() {
            markerOnClickHandler(marker, map, type);
        });
    }
    return marker;
}

function markerOnClickHandler(marker, map, type) {
    panMap(marker.getPosition(), marker.get('map'));
    if (type === 'starting') {
        hideMarkers(carpool_starting_markers);
        showMarkers(carpool_ending_markers, map);
        document.getElementById('from_latitude').value = marker.getPosition().lat();
        document.getElementById('from_longitude').value = marker.getPosition().lng();
    } else if (type === 'ending') {
        // submit form
        document.getElementById('to_latitude').value = marker.getPosition().lat();
        document.getElementById('to_longitude').value = marker.getPosition().lng();
        document.getElementById('submit').click();
    }
}

function loadMarkers(locations, map, type, hidden) {
    if (locations !== undefined && locations.length > 0) {
        for (loc of locations) {
            if (hidden) {
                map = null;
            }
            var marker = addMarker({lat: loc.lat, lng: loc.lng}, map, type);
            if (type === 'starting') {
                carpool_starting_markers.push(marker);
            }
            else if (type === 'ending') {
                carpool_ending_markers.push(marker);
            }
        }
    }
}

function hideMarkers(markers) {
    for (marker of markers) {
        marker.setMap(null);
    }
}

function showMarkers(markers, map) {
    for (marker of markers) {
        marker.setMap(map);
    }
}


