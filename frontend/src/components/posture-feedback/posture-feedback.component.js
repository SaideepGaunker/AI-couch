/**
 * Posture Feedback Component
 * Displays real-time posture feedback during interviews
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('postureFeedback', {
            templateUrl: 'components/posture-feedback/posture-feedback.template.html',
            controller: 'PostureFeedbackController',
            controllerAs: 'vm',
            bindings: {
                feedback: '<',
                isVisible: '<',
                compact: '<'
            }
        });
})();