


// ======= GOOGLE MAPS ===========

  // Virginia locations
  var westva = {lat: 38.7624, lng: -79.7170677};
  var sweetbriar = {lat: 37.5551696, lng: -79.098562};

  // Baltimore locations
  var baltLocations = [
    {lat: 39.3146481, lng: -76.6419097}, 
    {lat: 39.336027, lng: -76.574490}, 
    {lat: 39.278518, lng: -76.640065}, 
    {lat: 39.277858, lng: -76.542218}, 
    {lat: 39.351572, lng: -76.641438}
  ];
  var baltCenter = {lat: 39.314246, lng: -76.601955};
  var markers = [];
  var mapFindRide, mapGiveRide, mapMyRides, mapMini;

function initFindRideMap() {

  mapFindRide = new google.maps.Map(document.getElementById('background-map'), {
    zoom: 12,
    center: baltCenter,
    styles: mapStyleDiscreet
  });

  for (var i=0; i < baltLocations.length; i++) {
    markers.push(
      new google.maps.Marker({
        position: new google.maps.LatLng(baltLocations[i].lat, baltLocations[i].lng),
        map: mapFindRide,
        icon: normalIcon()
      })
    );
  }
}

function initGiveRideMap() {

  mapGiveRide = new google.maps.Map(document.getElementById('give-ride-map'), {
    zoom: 12,
    center: baltCenter,
    styles: mapStyleDiscreet
  });

  for (var i=0; i < baltLocations.length; i++) {
    markers.push(
      new google.maps.Marker({
        position: new google.maps.LatLng(baltLocations[i].lat, baltLocations[i].lng),
        map: mapGiveRide,
        icon: normalIcon()
      })
    );
  }
}

function initMyRidesMap() {

  mapMyRides = new google.maps.Map(document.getElementById('my-rides-map'), {
    zoom: 12,
    center: baltCenter,
    styles: mapStyleDiscreet
  });

  for (var i=0; i < baltLocations.length; i++) {
    markers.push(
      new google.maps.Marker({
        position: new google.maps.LatLng(baltLocations[i].lat, baltLocations[i].lng),
        map: mapMyRides,
        icon: normalIcon()
      })
    );
  }
}

function initMiniMap() {

  mapMini = new google.maps.Map(document.getElementById('mini-map'), {
    zoom: 12,
    center: baltCenter,
    styles: mapStyleDiscreet
  });

  new google.maps.Marker({
    position: new google.maps.LatLng(baltCenter.lat, baltCenter.lng),
    map: mapMini,
    icon: normalIcon()
  });
}

function normalIcon() {
  return {
    url: 'img/ic_marker_inactive.svg'
  };
}
function highlightedIcon() {
  return {
    url: 'img/ic_marker_active.svg'
  };
}

var activeDetail = false;
var navMenuOpen = false;

$(document).ready(function() {
  $('.logo').click( function() {
    if ($(window).width() <= 1200) {
      if (navMenuOpen == false) {
        navMenuOpen = true;
        $('.mobile-nav-bar').addClass('visible');
      } else {
        navMenuOpen = false;
        $('.mobile-nav-bar').removeClass('visible');
      }
    };
  });
  $('.results-box .result').hover(
    // mouse in
    function () {
      var index = $('.results-box .result').index(this);
      markers[index].setIcon(highlightedIcon());

    },
    // mouse out
    function () {
      var index = $('.results-box .result').index(this);
      markers[index].setIcon(normalIcon());
    }
  );
  $('.results-box .result').click( function () {
    if (activeDetail == false) {
      // open detail panel
      activeDetail = true;
      $('.right-bar').addClass("active");
      // recenter map on current marker
      var index = $('.results-box .result').index(this);
      console.log(markers[index].position);
      if ($(this).parent().hasClass('find-ride')) {
        mapFindRide.setCenter(markers[index].position);
      } else if ($(this).parent().hasClass('give-ride')) {
        mapGiveRide.setCenter(markers[index].position);
      } else if ($(this).parent().hasClass('my-rides')) {
        mapMyRides.setCenter(markers[index].position);
      }
    } else {
      // close detail panel
      activeDetail = false;
      $('.right-bar').removeClass("active");
    }
  });
  $("#gender-select").change(function () {
    if ($("#gender-select").val() == "other") {
      $('.gender-description').addClass('visible');
    } else {
      $('.gender-description').removeClass('visible');
    }
  });
});


