function CrossCheckXBlockShow(runtime, element) {

    function xblock($, _)
    {
        var uploadUrl = runtime.handlerUrl(element, 'upload_assignment');
        var downloadUrl = runtime.handlerUrl(element, 'download_uploaded');
        var approveUrl = runtime.handlerUrl(element, 'approve_assignment');
        var rollUrl = runtime.handlerUrl(element, 'roll_submission');

        var get_template = function(tmpl){
            return _.template($(element).find(tmpl).text());
        };

        var template = {
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
              select: get_template("#crosscheck-grading-select"),
              grade: get_template("#crosscheck-grading-grade")
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

            state.download_uploaded = downloadUrl;

            if (state.message != undefined) {
                append_content(template.common.message(state.message))
            }

            if (state.is_uploaded) {
                append_content(template.upload.info(state));
            }

            /*
             * This condition actually says whether collection step is in place,
             * not whether user can sent his submission.
             */
            if (state.is_collection_phase) {

                /*
                 * Show information about uploaded file.
                 */
                if (state.is_uploaded) {
                    append_content(template.common.file_info(state));
                }

                /*
                 * If user has not already approved his submission, he can always re-upload it.
                 */
                if (!state.sent_to_peers) {

                    /*
                     * Upload form
                     */
                    append_content(template.upload.main(state));

                    /*
                     * Set up upload controllers
                     */
                    var upload_logic = {
                        url: uploadUrl,
                        add: function (e, data) {
                            /*
                             * Render "upload another / selected" template
                             */
                            var do_upload = $(content).find('.upload').html(template.upload.selected({
                                'filename': data.files[0].name
                            }));
                            $(content).find(".upload_another").click(function () {
                                $(content).find('.upload').html(template.upload.input())
                                $(content).find(".file_upload").fileupload(upload_logic);
                            });
                            $(content).find(".upload_do").click(function () {
                                do_upload.text("Uploading...");
                                data.submit();
                            });
                        },
                        progressall: function (e, data) {
                            var percent = parseInt(data.loaded / data.total * 100, 10);
                            $(content).find(".upload").text("Uploading... " + percent + "%");
                        },
                        done: function (e, data) {
                            /* When you try to upload a file that exceeds Django's size
                             * limit for file uploads, Django helpfully returns a 200 OK
                             * response with a JSON payload of the form:
                             *
                             *   {'success': '<error message'}
                             *
                             * This is perfectly reasonable.  Unimpeachable even.  Makes
                             * perfect sense.
                             */
                            if (data.result.success !== undefined) {
                                // Actually, this is an error
                                state.error = data.result.success;
                                render(state);
                            }
                            else {
                                render(data.result);
                            }
                        }
                    };

                    /*
                     * Initialize default template to render
                     */
                    $(content).find('.upload').html(template.upload.input());
                    $(content).on("click", ".file_upload", function(){
                        $(content).find(".file_upload").fileupload(upload_logic);
                    });

                    /*
                     * If user has uploaded file but not yet sent it to peers -- show button
                     */
                    if (state.is_uploaded) {
                        append_content(template.upload.approve(state));

                        $(content).on("click", ".upload_approve", function(){
                            $.ajax({
                                type: "POST",
                                url: approveUrl,
                                success: function(data){ render(data); }
                            });
                        });
                    }

                } else { // if not sent_to_peers

                    if (state.is_uploaded) {
                        append_content(template.upload.approved(state));
                    }

                } // if not sent_to_peers

            } else if (state.is_grading_phase) { // if state.upload_allowed

                    if (state.is_uploaded) {

                        if (state.is_selected) {
                            append_content(template.grading.grade(state));
                        } else {
                            append_content(template.grading.select(state));

                            $(content).on("click", ".roll-btn", function(){
                                $.ajax({
                                    type: "POST",
                                    url: rollUrl,
                                    success: function(data){ render(data); }
                                });
                            });
                        }

                    } else {
                        append_content(template.grading.empty(state));
                    }

            } else {

            }

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