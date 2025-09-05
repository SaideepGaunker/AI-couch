/**
 * Title Case Filter
 * Converts text to title case for display purposes
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .filter('titleCase', titleCaseFilter);

    function titleCaseFilter() {
        return function(input) {
            if (!input || typeof input !== 'string') {
                return input;
            }

            // Convert camelCase and snake_case to words
            var words = input
                .replace(/([A-Z])/g, ' $1') // Add space before capital letters
                .replace(/_/g, ' ') // Replace underscores with spaces
                .replace(/\s+/g, ' ') // Replace multiple spaces with single space
                .trim()
                .toLowerCase()
                .split(' ');

            // Capitalize first letter of each word
            return words.map(function(word) {
                return word.charAt(0).toUpperCase() + word.slice(1);
            }).join(' ');
        };
    }
})();