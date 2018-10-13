let geocoder;
let map;
const defaultLat = 38.518;
const defaultLon = -97.328;
// geocoded from userQuery: { lat: 38, lng: -97 }
const nearLatLon = {};
// restrict results to US
const geocodeParams = { componentRestrictions: { country: 'US' } };
// { featureId: val }
const carpoolDistance = {};
// list of all geoJSON features
let carpoolFeatures = [];
// list of the markers currently appearing on the map
let markers = [];

/* eslint no-use-before-define: 0 */ // no-undef
/* eslint no-console: 0 */
/* global $: false, geoJSONUrl: false, google: false, map: true, mapStyleDiscreet: false, newCarpoolUrl: false */

/*
    externally defined globals
      map - Google Map object
      geoJSONUrl - URL to get carpool list GeoJSON
      newCarpoolUrl - URL to create new carpool
      destinationId - id of the current destination
      destinationLon - Longitude of destination
      destinationLat - Latitude of destination
*/

function setLatLng(lat, lng) {
    nearLatLon.lat = lat;
    nearLatLon.lng = lng;
    doSearch();
}

function localInitMap() {  // eslint-disable-line no-unused-vars
    // called from _template.html callback when Google Maps API loads
    map = new google.maps.Map(document.getElementById('background-map'), {
        center: { lat: defaultLat, lng: defaultLon },
        zoom: 3,
        styles: mapStyleDiscreet
    });
    geocoder = new google.maps.Geocoder();
    showDestinationQuery();
    setLatLng(destinationLat, destinationLon);
}

function doSearch() {
    // get all carpool results as GeoJSON
    var results = $('#search-results');
    results.empty();
    map.data.forEach(function(feature) {
        map.data.remove(feature);
    });
    for (let i = 0; i < markers.length; i++) {
        markers[i].setMap(null);
    }
    markers = [];

    const params = '?near.lat=' + nearLatLon.lat + '&near.lon=' + nearLatLon.lng;

    map.data.loadGeoJson(geoJSONUrl + params, null, mapDataCallback);
}

function deg2rad(deg) {
    return deg * (Math.PI / 180);
}

function distance(lat2, lng2) {
    // use Haversine formula to calculate approximate distance between
    // nearLatLon and this point
    // https://stackoverflow.com/questions/27928/calculate-distance-between-two-latitude-longitude-points-haversine-formula
    const lat1 = nearLatLon.lat;
    const lng1 = nearLatLon.lng;
    // distance in km
    const dLat = deg2rad(lat2 - lat1);
    const dLng = deg2rad(lng2 - lng1);
    const a = (Math.sin(dLat / 2) * Math.sin(dLat / 2)) +
        (Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
         Math.sin(dLng / 2) * Math.sin(dLng / 2));
    return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function geocodeResults(results, status) {
    // got lat/lng for user query
    if (status == 'OK') {
        const location = results[0].geometry.location;
        console.log('event: geocode result=', results[0], location.lat(), location.lng());
        setLatLng(location.lat(), location.lng());

        // save geocoding results
        const cache = JSON.parse(localStorage.getItem('geocode') || '{}');
        const key = userQuery.toLowerCase().trim();
        cache[key] = {
            ts: (new Date().getTime()),
            lat: location.lat(),
            lng: location.lng()
        };
        localStorage.setItem('geocode', JSON.stringify(cache));
    } else {
        // set error under input
        $('.geocode-error').show();
    }
}

function showCarpoolDetails(carpoolId) {
    window.location = carpoolId;
    return;
}

function showCarpoolDetailsDivClickHandler(event) {
    showCarpoolDetails(event.data);
}

function sortFeaturesByDistance(features) {
    // set distance from requested location
    features.forEach(function(feature) {
        const geo = feature.getGeometry().get();
        // extract id from URL
        const id = feature.getId().replace(/.*?\/carpools\/(.*)/, '$1');
        feature.setProperty('carpoolId', id);
        carpoolDistance[feature.getProperty('carpoolId')] = distance(geo.lat(), geo.lng());
    });
    // sort by distance
    return features.sort(function(a, b) {
        return carpoolDistance[a.getProperty('carpoolId')] - carpoolDistance[b.getProperty('carpoolId')];
    });
}

function zoomMap() {
    let features = [];
    if (nearLatLon.lat) {
        console.log('zooming to nearLatLon', nearLatLon);
        // if nearLatLon, zoom to nearLatLon +- 100km or minimum 3 closest features
        features = carpoolFeatures.slice(0, 3);
        carpoolFeatures.slice(3).forEach(function(feature) {
            if (carpoolDistance[feature.getId()] < 100) {
                features.push(feature);
            }
        });
    } else {
        // else fit to all features
        features = carpoolFeatures;
    }

    if (!features.length) {
        // no carpools: zoom to requested location
        if (nearLatLon.lat) {
            map.setCenter(new google.maps.LatLng(nearLatLon.lat, nearLatLon.lng));
            map.setZoom(11);
        }
        return;
    }
    // fit map to set of features
    const bounds = new google.maps.LatLngBounds();
    features.forEach(function (feature) {
        const geo = feature.getGeometry().get();
        bounds.extend(new google.maps.LatLng(geo.lat(), geo.lng()));
    });
    if (nearLatLon.lat) {
        // include search location
        bounds.extend(new google.maps.LatLng(nearLatLon.lat, nearLatLon.lng));
    }
    map.fitBounds(bounds);
}


function showDestinationQuery() {
    $('#search-results').append('<div class="result">' +
        '<h3>Loading carpools for this destination ...</h3>' +
        '</div>');
}

function showNoResults(text) {
    $('#search-results').append('<div class="result">' +
        '<h3>No carpools nearby.</h3>' +
        '<p>Will you consider <a href="' + newCarpoolUrl + '">starting one</a>?</p>' +
        '</div>');
}

function showLoginPrompt(){
    $('#search-results').append('<div style="padding-top: 20px; display: inline-flex;">' +
        '<h3 style="margin-right: 10px; padding-top: 4px;">Log in to see more carpools</h3>' +
        '<a href="/login"><button class="btn btn-primary">Login</button></a>' +
        '</div>');
}

function mapDataCallback(features) {
    console.log('event: loaded features');
    var results = $('#search-results');
    results.empty();

    if (features.length > 0) {
        // sort by distance
        carpoolFeatures = sortFeaturesByDistance(features);
        for (var i = 0; i < carpoolFeatures.length; i++) {
            const feature = features[i];
            if (destinationId !== feature.getProperty('destination_id')) {
                continue;
            }
            const geo = feature.getGeometry().get();

            const seatsAvailable = feature.getProperty('seats_available');
            let seatString = '<p>' + seatsAvailable + ' seats available</p>';
            if (seatsAvailable === 1 ) {
                seatString = '<p>' + seatsAvailable + ' seat available</p>';
            } else if (seatsAvailable < 1) {
                seatString = '<p>No seats available</p>';
            }

            var resultdiv = $(
                '<div class="result" id="' + feature.getProperty('carpoolId') + '" data-lat="' + geo.lat() + '" data-lng="' + geo.lng() + '">' +
                    '<h3 class="result-title">' +
                        feature.getProperty('from_place') + ' to ' + feature.getProperty('to_place') +
                    '</h3>' + seatString +
                    '<p>Departs: ' + feature.getProperty('leave_time_human') + '</p>' +
                    '<p>Returns: ' + feature.getProperty('return_time_human') + '</p>' +
                    '<p>Destination: '+ feature.getProperty('to_place') + '</p>' +
                '</div>');
            resultdiv.click(feature.getId(), showCarpoolDetailsDivClickHandler);
            results.append(resultdiv);
        }

        map.data.setStyle(function(feature) {
            if (destinationId !== feature.getProperty('destination_id')) {
                return { visible: false };
            }
            if (feature.getProperty('is_approximate_location')) {
                var geo = feature.getGeometry();
                var marker = new google.maps.Marker({
                    position: geo.get(),
                    icon: {
                        path: google.maps.SymbolPath.CIRCLE,
                        fillColor: '#3090C7',
                        fillOpacity: 0.5,
                        scale: 25,
                        strokeWeight: 0
                    },
                    draggable: false,
                    map: map,
                    url: feature.getId(),
                });
                marker.addListener('click', function() {
                    window.location.href = this.url;
                });
                feature.marker = marker;
                markers.push(marker);
                return { visible: false };
            } else {
                return {
                    icon: 'https://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|3090C7'
                };
            }
        });
        zoomMap();
        google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
            if (this.getZoom() > 11) {
                this.setZoom(11);
            }
        });
    } else {
        zoomMap();
        showNoResults();
    }

    if (!userAuthenticated){
        showLoginPrompt();
    }

    results.addClass('results-box');

    map.data.addListener('click', function(event) {
        showCarpoolDetails(event.feature.getId());
    });
}
