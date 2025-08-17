/**
 * Posture Feedback Controller
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('PostureFeedbackController', PostureFeedbackController);

    PostureFeedbackController.$inject = ['$scope'];

    function PostureFeedbackController($scope) {
        var vm = this;

        // Properties
        vm.feedback = null;
        vm.isVisible = true;
        vm.compact = false;

        // Methods
        vm.getStatusColor = getStatusColor;
        vm.getStatusIcon = getStatusIcon;
        vm.getScoreColor = getScoreColor;
        vm.formatScore = formatScore;

        // Initialize
        activate();

        function activate() {
            // Watch for feedback changes
            $scope.$watch('vm.feedback', function(newFeedback) {
                if (newFeedback) {
                    vm.feedback = newFeedback;
                }
            });
        }

        /**
         * Get color class based on posture status
         */
        function getStatusColor(status) {
            switch (status) {
                case 'good':
                    return 'success';
                case 'needs_improvement':
                    return 'warning';
                case 'bad':
                    return 'danger';
                case 'no_pose':
                    return 'secondary';
                default:
                    return 'secondary';
            }
        }

        /**
         * Get icon based on posture status
         */
        function getStatusIcon(status) {
            switch (status) {
                case 'good':
                    return 'fas fa-check-circle';
                case 'needs_improvement':
                    return 'fas fa-exclamation-triangle';
                case 'bad':
                    return 'fas fa-times-circle';
                case 'no_pose':
                    return 'fas fa-user-slash';
                default:
                    return 'fas fa-question-circle';
            }
        }

        /**
         * Get color class based on score
         */
        function getScoreColor(score) {
            if (score >= 80) return 'success';
            if (score >= 60) return 'warning';
            return 'danger';
        }

        /**
         * Format score for display
         */
        function formatScore(score) {
            return Math.round(score || 0);
        }
    }
})();