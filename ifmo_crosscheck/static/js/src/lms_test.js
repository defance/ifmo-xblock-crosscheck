function CrossCheckXBlockShow(runtime, element) {

    function xblock($, _)
    {
        var uploadUrl = runtime.handlerUrl(element, 'upload_assignment');
        var downloadUrl = runtime.handlerUrl(element, 'download_uploaded');
        var approveUrl = runtime.handlerUrl(element, 'approve_assignment');

        var get_template = function(tmpl){
            return _.template($(element).find(tmpl).text());
        };

        var template = {
          temp: get_template("#crosscheck-temp"),
          upload: {
              main: get_template("#crosscheck-upload-template"),
              info: get_template("#crosscheck-upload-info"),
              input: get_template("#crosscheck-upload-input"),
              selected: get_template("#crosscheck-upload-selected"),
              approve: get_template("#crosscheck-upload-approve"),
              approved: get_template("#crosscheck-upload-approved")
          },
          grading: {
              empty: get_template("#crosscheck-grading-empty"),
              select: get_template("#crosscheck-grading-select")
          },
          common: {
              file_info: get_template("#crosscheck-file-info"),
              message: get_template("#crosscheck-message")
          }
        };

        /**
         * Rendering solution uploads
         * TODO: Refactor all this logic
         */
        function render(state)
        {
            var content = $(element).find("#crosscheck-content").html('');
            var append_content = function (data) {
                content.html(content.html() + data);
            };

            append_content(template.temp());

            var upload_logic = {
                url: uploadUrl,
                add: function (e, data) {
                    alert("add");
                }
            };

            var control = $(element).find('.fu');
            control.bind('click', function(e){
                control.fileupload(upload_logic);
            });

        }


        $(function($) { // onLoad

            var block = $(element).find(".crosscheck-block");
            var state = block.attr("data-state");

            render(JSON.parse(state));
        });

    }

    /**
     * The following initialization code is taken from edx-SGA XBlock.
     */
    if (require === undefined) {
        /**
         * The LMS does not use require.js (although it loads it...) and
         * does not already load jquery.fileupload.  (It looks like it uses
         * jquery.ajaxfileupload instead.  But our XBlock uses
         * jquery.fileupload.
         */
        function loadjs(url) {
            $("<script>")
                .attr("type", "text/javascript")
                .attr("src", url)
                .appendTo(element);
        }
        loadjs("/static/js/vendor/jQuery-File-Upload/js/jquery.iframe-transport.js");
        loadjs("/static/js/vendor/jQuery-File-Upload/js/jquery.fileupload.js");
        xblock($, _);
    }
    else {
        /**
         * Studio, on the other hand, uses require.js and already knows about
         * jquery.fileupload.
         */
        require(["jquery", "underscore", "jquery.fileupload"], xblock);
    }

}