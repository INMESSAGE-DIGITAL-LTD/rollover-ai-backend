(function ($) {
  $(document).on('ready', function () {

    $('.js-doughnut-chart').each(function (i, el) {
      var data = JSON.parse(el.getAttribute('data-set')),
        colors = JSON.parse(el.getAttribute('data-colors'));

      var chart = new Chart(el, {
        type: 'doughnut',
        data: {
          datasets: [{
            backgroundColor: colors,
            data: data
          }]
        },
        options: {
          legend: {
            display: false
          },
          tooltips: {
            enabled: false
          },
          cutoutPercentage: 87
        }
      });
    });
  });
})(jQuery);