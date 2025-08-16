/**
 * Feedback Component - Shows interview results and performance analysis
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('feedbackComponent', {
            templateUrl: 'components/feedback/feedback.template.html',
            controller: 'FeedbackController',
            controllerAs: 'vm'
        });
})();