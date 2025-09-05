/**
 * Difficulty Display Service - Handles difficulty level display and formatting
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('DifficultyDisplayService', DifficultyDisplayService);

    DifficultyDisplayService.$inject = ['$log'];

    function DifficultyDisplayService($log) {
        var service = {
            // Difficulty level management
            getDifficultyLevels: getDifficultyLevels,
            getDifficultyLabel: getDifficultyLabel,
            getDifficultyColor: getDifficultyColor,
            getDifficultyIcon: getDifficultyIcon,
            getDifficultyDescription: getDifficultyDescription,
            
            // Difficulty calculation
            calculateDifficulty: calculateDifficulty,
            formatDifficultyScore: formatDifficultyScore,
            
            // Display utilities
            getDifficultyBadgeClass: getDifficultyBadgeClass,
            getDifficultyProgressClass: getDifficultyProgressClass,
            
            // Input normalization and conversion
            normalizeDifficultyInput: normalizeDifficultyInput,
            getStringLevel: getStringLevel,
            
            // Complete difficulty information
            getDifficultyInfo: getDifficultyInfo
        };

        // Difficulty level definitions
        var difficultyLevels = {
            1: {
                label: 'Easy',
                color: '#28a745',
                icon: 'fas fa-leaf',
                description: 'Simple questions with straightforward answers',
                range: [0, 30]
            },
            2: {
                label: 'Medium',
                color: '#fd7e14',
                icon: 'fas fa-balance-scale',
                description: 'Moderate complexity requiring some experience',
                range: [31, 60]
            },
            3: {
                label: 'Hard',
                color: '#dc3545',
                icon: 'fas fa-mountain',
                description: 'Challenging questions for experienced professionals',
                range: [61, 80]
            },
            4: {
                label: 'Expert',
                color: '#6f42c1',
                icon: 'fas fa-crown',
                description: 'Advanced questions for senior-level positions',
                range: [81, 100]
            }
        };

        /**
         * Get complete difficulty information
         * @param {number} level - Difficulty level (1-4)
         * @returns {Object} Complete difficulty information
         */
        function getDifficultyInfo(level) {
            if (!level || !difficultyLevels[level]) {
                return {
                    level: 0,
                    label: 'Unknown',
                    color: '#6c757d',
                    icon: 'fas fa-question-circle',
                    description: 'Difficulty level not specified',
                    badgeClass: 'badge bg-secondary',
                    progressClass: 'progress-bar bg-secondary'
                };
            }

            var difficulty = difficultyLevels[level];
            return {
                level: parseInt(level),
                label: difficulty.label,
                color: difficulty.color,
                icon: difficulty.icon,
                description: difficulty.description,
                badgeClass: getDifficultyBadgeClass(level),
                progressClass: getDifficultyProgressClass(level),
                range: difficulty.range
            };
        }

        return service;

        // ==================== Input Normalization and Conversion ====================

        /**
         * Normalize difficulty input to numeric level (1-5)
         * @param {string|number} input - Difficulty input (string like 'easy', 'medium' or numeric level)
         * @returns {number} Normalized difficulty level (1-5)
         */
        function normalizeDifficultyInput(input) {
            if (typeof input === 'number') {
                // Already numeric, ensure it's in valid range
                return Math.max(1, Math.min(5, Math.round(input)));
            }
            
            if (typeof input === 'string') {
                var normalized = input.toLowerCase().trim();
                
                // Map string values to numeric levels
                switch (normalized) {
                    case 'easy':
                        return 1;
                    case 'medium':
                    case 'moderate':
                        return 2;
                    case 'hard':
                    case 'difficult':
                        return 3;
                    case 'expert':
                    case 'advanced':
                        return 4;
                    default:
                        // Try to parse as number
                        var parsed = parseInt(normalized);
                        if (!isNaN(parsed)) {
                            return Math.max(1, Math.min(4, parsed));
                        }
                        // Default to medium if unrecognized
                        return 2;
                }
            }
            
            // Default fallback
            return 2;
        }

        /**
         * Convert numeric difficulty level to string representation
         * @param {number} level - Numeric difficulty level (1-4)
         * @returns {string} String representation ('easy', 'medium', etc.)
         */
        function getStringLevel(level) {
            var normalizedLevel = normalizeDifficultyInput(level);
            
            switch (normalizedLevel) {
                case 1:
                    return 'easy';
                case 2:
                    return 'medium';
                case 3:
                    return 'hard';
                case 4:
                    return 'expert';
                default:
                    return 'medium';
            }
        }

        // ==================== Difficulty Level Management ====================

        /**
         * Get all available difficulty levels
         * @returns {Object} Difficulty levels configuration
         */
        function getDifficultyLevels() {
            return difficultyLevels;
        }

        /**
         * Get difficulty label by level number
         * @param {number} level - Difficulty level (1-5)
         * @returns {string} Difficulty label
         */
        function getDifficultyLabel(level) {
            if (!level || !difficultyLevels[level]) {
                return 'Unknown';
            }
            return difficultyLevels[level].label;
        }

        /**
         * Get difficulty color by level number
         * @param {number} level - Difficulty level (1-5)
         * @returns {string} Color hex code
         */
        function getDifficultyColor(level) {
            if (!level || !difficultyLevels[level]) {
                return '#6c757d'; // Default gray
            }
            return difficultyLevels[level].color;
        }

        /**
         * Get difficulty icon by level number
         * @param {number} level - Difficulty level (1-5)
         * @returns {string} Font Awesome icon class
         */
        function getDifficultyIcon(level) {
            if (!level || !difficultyLevels[level]) {
                return 'fas fa-question-circle';
            }
            return difficultyLevels[level].icon;
        }

        /**
         * Get difficulty description by level number
         * @param {number} level - Difficulty level (1-5)
         * @returns {string} Difficulty description
         */
        function getDifficultyDescription(level) {
            if (!level || !difficultyLevels[level]) {
                return 'Difficulty level not specified';
            }
            return difficultyLevels[level].description;
        }

        // ==================== Difficulty Calculation ====================

        /**
         * Calculate difficulty level based on score
         * @param {number} score - Score value (0-100)
         * @returns {number} Difficulty level (1-5)
         */
        function calculateDifficulty(score) {
            if (typeof score !== 'number' || score < 0) {
                return 1;
            }

            for (var level in difficultyLevels) {
                var range = difficultyLevels[level].range;
                if (score >= range[0] && score <= range[1]) {
                    return parseInt(level);
                }
            }

            // Default to highest level if score exceeds ranges
            return 5;
        }

        /**
         * Format difficulty score for display
         * @param {number} score - Raw difficulty score
         * @param {Object} options - Formatting options
         * @returns {string} Formatted score string
         */
        function formatDifficultyScore(score, options) {
            options = options || {};
            
            if (typeof score !== 'number') {
                return 'N/A';
            }

            var formattedScore = score.toFixed(options.decimals || 1);
            
            if (options.showPercentage) {
                return formattedScore + '%';
            }
            
            if (options.showOutOf) {
                return formattedScore + '/' + (options.maxScore || 100);
            }
            
            return formattedScore;
        }

        // ==================== Display Utilities ====================

        /**
         * Get CSS class for difficulty badge
         * @param {number} level - Difficulty level (1-5)
         * @returns {string} CSS class string
         */
        function getDifficultyBadgeClass(level) {
            var baseClass = 'badge';
            
            switch (level) {
                case 1:
                    return baseClass + ' bg-success';
                case 2:
                    return baseClass + ' bg-info';
                case 3:
                    return baseClass + ' bg-warning';
                case 4:
                    return baseClass + ' bg-danger';
                case 5:
                    return baseClass + ' bg-dark';
                default:
                    return baseClass + ' bg-secondary';
            }
        }

        /**
         * Get CSS class for difficulty progress bar
         * @param {number} level - Difficulty level (1-5)
         * @returns {string} CSS class string
         */
        function getDifficultyProgressClass(level) {
            var baseClass = 'progress-bar';
            
            switch (level) {
                case 1:
                    return baseClass + ' bg-success';
                case 2:
                    return baseClass + ' bg-info';
                case 3:
                    return baseClass + ' bg-warning';
                case 4:
                    return baseClass + ' bg-danger';
                case 5:
                    return baseClass + ' bg-dark';
                default:
                    return baseClass + ' bg-secondary';
            }
        }

        // ==================== Public Convenience Methods ====================



        /**
         * Get difficulty by score with complete information
         * @param {number} score - Score value (0-100)
         * @returns {Object} Complete difficulty information
         */
        service.getDifficultyByScore = function(score) {
            var level = calculateDifficulty(score);
            return getDifficultyInfo(level);
        };

        /**
         * Format difficulty for display with icon and label
         * @param {number} level - Difficulty level (1-5)
         * @param {Object} options - Display options
         * @returns {string} HTML string for display
         */
        service.formatDifficultyDisplay = function(level, options) {
            options = options || {};
            var info = service.getDifficultyInfo(level);
            
            var html = '';
            
            if (options.showIcon !== false) {
                html += '<i class="' + info.icon + '" style="color: ' + info.color + ';"></i> ';
            }
            
            if (options.showBadge) {
                html += '<span class="' + info.badgeClass + '">' + info.label + '</span>';
            } else {
                html += '<span style="color: ' + info.color + ';">' + info.label + '</span>';
            }
            
            if (options.showDescription) {
                html += '<br><small class="text-muted">' + info.description + '</small>';
            }
            
            return html;
        };

        $log.debug('DifficultyDisplayService initialized');
    }
})();