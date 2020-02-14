(function(Modules) {
  "use strict";

  if (!document.queryCommandSupported('copy')) return;

  Modules.ApiKey = function() {

    const states = {
      'keyVisible': (key, thing) => `
        <span class="api-key__key">${key}</span>
        <input type='button' class='govuk-button govuk-button--secondary api-key__button--copy' value='Copy ${thing} to clipboard' />
      `,
      'keyCopied': thing => `
        <span class="api-key__key">Copied to clipboard</span>
        <input type='button' class='govuk-button govuk-button--secondary api-key__button--show' value='Show ${thing}' />
      `
    };

    this.copyKey = function(keyElement, callback) {
      var selection = window.getSelection ? window.getSelection() : document.selection,
          range = document.createRange();
      selection.removeAllRanges();
      range.selectNodeContents(keyElement);
      selection.addRange(range);
      document.execCommand('copy');
      selection.removeAllRanges();
      callback();
    };

    this.start = function(component) {

      const $component = $(component),
            key = $component.data('key'),
            thing = $component.data('thing');

      $component
        .addClass('api-key')
        .css('min-height', $component.height())
        .html(states.keyVisible(key, thing))
        .attr('aria-live', 'polite')
        .on(
          'click', '.api-key__button--copy', () =>
            this.copyKey(
              $('.api-key__key', component)[0], () =>
                $component.html(states.keyCopied(thing))
            )
        )
        .on(
          'click', '.api-key__button--show', () =>
            $component.html(states.keyVisible(key, thing))
        );

      if ('stickAtBottomWhenScrolling' in GOVUK) {
        GOVUK.stickAtBottomWhenScrolling.recalculate();
      }

    };
  };

})(window.GOVUK.Modules);
