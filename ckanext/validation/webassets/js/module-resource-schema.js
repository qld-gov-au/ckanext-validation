 /* Image Upload
 *
 */
this.ckan.module('resource-schema', function($) {
  return {
    /* options object can be extended using data-module-* attributes */
    options: {
      is_url: false,
      is_upload: false,
      is_json: false,
      field_upload: 'schema_upload',
      field_url: 'schema_url',
      field_json: 'schema_json',
      field_schema: 'schema',
      field_clear: 'clear_upload',
      field_name: 'name',
      upload_label: '',
      hide_upload: false,
      hide_remote: false,
      hide_inline: false,
    },

    /* Should be changed to true if user modifies resource's name
     *
     * @type {Boolean}
     */
    _nameIsDirty: false,

    /* Initialises the module setting up elements and event listeners.
     *
     * Returns nothing.
     */
    initialize: function () {
      $.proxyAll(this, /_on/);
      var options = this.options;

      var field_upload = 'input[name="' + options.field_upload + '"]';
      var field_url = 'input[name="' + options.field_url + '"]';
      var field_json = 'textarea[name="' + options.field_json +'"]';
      var field_schema = 'input[name="' + options.field_schema +'"]';

      this.align_block = $(".schema-align")
      this.field_align = $('#' + options.align_id);

      this.input = $(field_url, this.el);
      this.field_upload = $(field_upload, this.el).parents('.form-group');
      this.field_url = $(field_url, this.el).parents('.form-group');
      this.field_json = $(field_json, this.el).parents('.form-group');

      if (!this.field_upload.length) {
        this.field_upload = $(field_upload, this.el).parents('.control-group');
        this.field_url = $(field_url, this.el).parents('.control-group');
        this.field_json = $(field_json, this.el).parents('.control-group');

      }

      this.field_upload_input = $('input', this.field_upload);
      this.field_url_input = $('input', this.field_url);
      this.field_json_input = $('textarea', this.field_json);
      this.field_schema_input = $(field_schema);

      // this is the location for the upload/link data/image label
      this.buttons_div = $("#resource-schema-buttons");
      this.label = $('label', this.buttons_div);

      this.label_url = $('label', this.field_url);

      this.field_upload_input.on('change', this._onInputChange);
      this.field_url_input.focus()
        .on('blur', this._onURLBlur);
      this.field_json_input.focus()
        .on('blur', this._onJSONBlur);
      this.field_json_input.on('input', this._onJsonChange);

      // Button to set upload a schema file
      this.button_upload = $('<a href="javascript:;" class="btn btn-default">' +
                          '<i class="fa fa-cloud-upload"></i>' +
                          this._('Upload') + '</a>')
        .prop('title', this._('Upload a Data Schema file from your computer'))
        .on('click', this._onFromUpload);
      $('.controls', this.buttons_div).append(this.button_upload);

      // Button to set the field to be a URL
      this.button_url = $('<a href="javascript:;" class="btn btn-default">' +
                          '<i class="fa fa-globe"></i>' +
                          this._('Link') + '</a>')
        .prop('title', this._('URL for a Data Schema file available on the Internet'))
        .on('click', this._onFromWeb);
      $('.controls', this.buttons_div).append(this.button_url);

      // Button to set the field to be a JSON text
      this.button_json = $('<a href="javascript:;" class="btn btn-default">' +
                          '<i class="fa fa-code"></i>' +
                          this._('JSON') + '</a>')
        .prop('title', this._('Enter manually a Table Schema JSON object'))
        .on('click', this._onFromJSON);
      $('.controls', this.buttons_div).append(this.button_json);

      var removeText = this._('Clear');

      // Change the clear file upload button too
       $('.btn.btn-danger.btn-remove-url').text(removeText).removeClass('btn-danger').addClass('btn-default');

      // Button for resetting the form when there is a URL set
      $('<a href="javascript:;" class="btn btn-default btn-remove-url">'
        + removeText + '</a>')
        .prop('title', removeText)
        .on('click', this._onRemoveURL)
        .insertBefore(this.field_url_input);

      // Button for resetting the form when there is a JSON text set
      $('<a href="javascript:;" class="btn btn-default btn-remove-url">'
        + removeText + '</a>')
        .prop('title', removeText)
        .on('click', this._onRemoveJSON)
        .insertBefore(this.field_json_input);

      // Fields storage. Used in this.changeState
      this.fields = $('<i />')
        .add(this.button_upload)
        .add(this.button_url)
        .add(this.button_json)
        .add(this.field_upload)
        .add(this.field_url)
        .add(this.field_json);

      if (options.is_url) {
        this._showOnlyFieldUrl();
      } else if (options.is_json) {
        this._showOnlyFieldJSON();
      } else {
        this._showOnlyButtons();
      }
    },

    /* Update the `this.label` text
     *
     * If the upload/link is for a data resource, rather than an image,
     * the text for label[for="field-image-url"] will be updated.
     *
     * label_text - The text for the label of an uploaded/linked resource
     *
     * Returns nothing.
     */
    _updateUrlLabel: function(label_text) {
      this.label.text(label_text);
    },

    _onFromUpload: function() {

      this.field_upload_input.click()

    },

    /* Event listener for when someone sets the field to URL mode
     *
     * Returns nothing.
     */
    _onFromWeb: function() {
      this._showOnlyFieldUrl();

      this.field_url_input.focus()
        .on('blur', this._onFromWebBlur);

    },

    /* Event listener for when someone sets the field to JSON text mode
     *
     * Returns nothing.
     */
    _onFromJSON: function() {
      this._showOnlyFieldJSON();

    },

    /* Event listener for resetting the URL field back to the blank state
     *
     * Returns nothing.
     */
    _onRemoveURL: function() {
      this._showOnlyButtons();

      this.field_url_input.val('');
      this.field_url_input.prop('readonly', false);

      this.field_schema_input.val('');

      this._updateUrlLabel(this._('Data Schema'));

      this.label_url.text(this._('Data Schema URL'))

      this._markUnaligned();
    },

    /* Event listener for resetting the JSON text field back to the blank state
     *
     * Returns nothing.
     */
    _onRemoveJSON: function() {
      this._showOnlyButtons();

      this.field_json_input.val('');
      this.field_json_input.prop('readonly', false);

      this.field_schema_input.val('');

      this._markUnaligned();
    },

    _showOnlyButtons: function() {
      this.fields.hide();
      this.label.show();
      !this.options.hide_upload && this.button_upload.show()
      !this.options.hide_url && this.button_url.show()
      !this.options.hide_json && this.button_json.show()
    },

    _showOnlyFieldUrl: function() {
      this.fields.hide();
      this.label.hide();
      this.field_url.show();
    },

    _showOnlyFieldJSON: function() {
      this.fields.hide();
      this.label.hide();
      this.field_json.show();
    },

    _onURLBlur: function() {
      var url = this.field_url_input.val();
      if (url) {
        this.field_schema_input.val(url);
      }
    },

    _onJSONBlur: function() {
      var json = this.field_json_input.val();
      if (json) {
        this.field_schema_input.val(json);
      }
    },

    _onInputChange: function() {
      var file_name = this.field_upload_input.val().split(/^C:\\fakepath\\/).pop();

      this.field_url_input.val(file_name);
      this.field_url_input.prop('readonly', true);

      this.label_url.text(this._('Uploaded Data Schema'))
      this._showOnlyFieldUrl();
    },

    _onJsonChange: function() {
        this._markUnaligned();
    },

    _fileNameFromUpload: function(url) {
      // If it's a local CKAN image return the entire URL.
      if (/^\/base\/images/.test(url)) {
        return url;
      }

      // remove fragment (#)
      url = url.substring(0, (url.indexOf("#") === -1) ? url.length : url.indexOf("#"));
      // remove query string
      url = url.substring(0, (url.indexOf("?") === -1) ? url.length : url.indexOf("?"));
      // extract the filename
      url = url.substring(url.lastIndexOf("/") + 1, url.length);

      return url; // filename
    },

    _markUnaligned: function() {
        if (this.align_block.hasClass("no-default-schema")) {
            return;
        }
        this.align_block.removeClass('hidden');
        this.field_align.prop('checked', false);
    }
  };
});
