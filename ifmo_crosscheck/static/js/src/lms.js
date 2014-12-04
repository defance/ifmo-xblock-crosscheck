function CrossCheckXBlockShow(runtime, element) {

    function xblock($, _)
    {
        var uploadUrl = runtime.handlerUrl(element, 'upload_assignment');
        var downloadUrl = runtime.handlerUrl(element, 'download_uploaded');
        var approveUrl = runtime.handlerUrl(element, 'approve_assignment');
        var rollUrl = runtime.handlerUrl(element, 'roll_submission');
        var gradeUrl = runtime.handlerUrl(element, 'grade');
        var rolledUrl = runtime.handlerUrl(element, 'download_rolled');

        var get_template = function(tmpl){
            return _.template($(element).find(tmpl).text());
        };


        var template = {
            main: get_template('#crosscheck-template'),
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


        function render_new(state) {

            state.message = state.message ? state.message : false;
            state.uploaded = state.uploaded ? state.uploaded : false;
            state.rolled = state.rolled ? state.rolled : false;
            state.score = state.score ? state.score : false;

            var block = $(element).find("#crosscheck-block")[0];
            var content = $(element).find("#crosscheck-content");

            if (state.uploaded) {
                state.uploaded.url = downloadUrl;
            }

            if (state.rolled) {
                state.rolled.url = gradeUrl;
                state.rolled.file_url = rolledUrl;
            }

            content.html(template.main(state));

            if (state.is_upload_allowed && (!state.uploaded || !state.uploaded.approved)) {
                $(content).find('.upload').html(template.upload.input());

                var upload_logic = {
                    url: uploadUrl,
                    add: function (e, data) {
                        $(content).find('.upload').html(template.upload.selected({
                            'filename': data.files[0].name
                        }));
                        $(content).find(".upload_another").on('click', function () {
                            $(content).find('.upload').html(template.upload.input());
                            $(content).find(".file_upload").fileupload(upload_logic);
                        });
                        $(content).find(".upload_do").on('click', function () {
                            $(content).find(".upload_do").text("Uploading...");
                            disable_controllers(content);
                            data.submit();
                        });
                    },
                    progressall: function (e, data) {
                        var percent = parseInt(data.loaded / data.total * 100, 10);
                        $(content).find(".upload_do").text("Uploading... " + percent + "%");
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
                            state.message = {
                                'message_type': 'error',
                                'message_text': data.result.success
                            };
                            render_new(state);
                        }
                        else {
                            render_new(data.result);
                        }
                    }
                };

                $(content).find(".file_upload").fileupload(upload_logic);
            }

            if (state.is_upload_allowed && state.uploaded && !state.approved) {
                // Is of really needed?
                $(content).off("click", ".upload_approve").on("click", ".upload_approve", function(){
                        var btn = $(content).find(".upload_approve");
                        btn.text(btn.attr("data-in-progress"));
                        disable_controllers(content);
                        $.ajax({ url: approveUrl, type: "POST", success: function(data){ render_new(data); }
                    });
                });
            }

            if (state.is_grading_allowed && !state.rolled) {
                $(content).off("click", ".roll_btn").on("click", ".roll_btn", function(){
                        var btn = $(content).find(".roll_btn");
                        btn.text(btn.attr("data-in-progress"));
                        disable_controllers(content);
                        $.ajax({ url: rollUrl, type: "POST", success: function(data){ render_new(data); }
                    });
                });
            }

            if (state.is_grading_allowed && state.rolled) {
                var form = $(content).find('#enter-grade-form');
                form.off("submit").on("submit", function(e){
                    e.preventDefault();
                    // Validate data
                    if (form.find("#grade-input").val() == '') {
                        $(".grade-form-message").text("Grade cannot be empty.").show();
                        return;
                    }
                    var score = Number(form.find("#grade-input").val());
                    var max_score = Number($('#crosscheck-block').data('max_score'));
                    if (isNaN(score)) {
                        $(".grade-form-message").text("Grade must be a number.").show();
                    } else if (score < 0) {
                        $(".grade-form-message").text("Grade must be positive.").show();
                    } else if (score > max_score) {
                        $(".grade-form-message").text("Maximum score is " + max_score + '.').show();
                    } else {
                        form.find("button").toggleClass("disabled").attr("disabled", "disabled");
                        $.post(gradeUrl, form.serialize()).success(render_new);
                    }
                });

            }

            if(state.score) {
                if (state.score.passed) {
                    $('.problem-progress').text('(' + state.score.score + '/' + state.score.total + ' points possible)');
                } else {
                    $('.problem-progress').text('(' + state.score.total + ' points possible)');
                }
            }

            $('.instructor-info-action').leanModal();

        }

        function disable_controllers(context) {
            $(context).find(".controllers").find("button").toggleClass('disabled').attr("disabled", "disabled");
        }

        $(function($) { // onLoad

            var block = $(element).find(".crosscheck-block");
            var state = block.attr("data-state");

            render_new(JSON.parse(state));
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