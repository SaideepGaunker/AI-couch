/**
 * Recommendations Display Component
 * Shows personalized learning recommendations based on performance
 */
(function() {
    'use strict';

    angular
        .module('interviewApp')
        .component('recommendationsDisplay', {
            templateUrl: 'components/recommendations/recommendations.template.html',
            controller: RecommendationsController,
            controllerAs: 'vm',
            bindings: {
                performanceScores: '<',
                userLevel: '<',
                targetRole: '<',
                onRecommendationClick: '&',
                onFeedback: '&',
                showTitle: '<',
                maxRecommendations: '<'
            }
        });

    RecommendationsController.$inject = ['$http', '$log', 'ApiService'];

    function RecommendationsController($http, $log, ApiService) {
        var vm = this;

        // Component properties
        vm.recommendations = [];
        vm.loading = false;
        vm.error = null;
        vm.feedbackSubmitted = {};

        // Public methods
        vm.$onInit = onInit;
        vm.$onChanges = onChanges;
        vm.loadRecommendations = loadRecommendations;
        vm.trackClick = trackClick;
        vm.submitFeedback = submitFeedback;
        vm.getRecommendationIcon = getRecommendationIcon;
        vm.getProviderBadgeClass = getProviderBadgeClass;
        vm.formatDuration = formatDuration;

        /**
         * Component initialization
         */
        function onInit() {
            $log.debug('RecommendationsDisplay: Initializing component');
            
            // Set defaults
            vm.showTitle = vm.showTitle !== false; // Default to true
            vm.maxRecommendations = vm.maxRecommendations || 4;
            
            // Load recommendations if we have performance data
            if (vm.performanceScores) {
                loadRecommendations();
            }
        }

        /**
         * Handle input changes
         */
        function onChanges(changes) {
            if (changes.performanceScores && !changes.performanceScores.isFirstChange()) {
                loadRecommendations();
            }
        }

        /**
         * Load personalized recommendations from API
         */
        function loadRecommendations() {
            if (!vm.performanceScores) {
                $log.debug('RecommendationsDisplay: No performance scores provided');
                return;
            }

            vm.loading = true;
            vm.error = null;

            var requestData = {
                performance_scores: vm.performanceScores,
                user_level: vm.userLevel || 'intermediate',
                target_role: vm.targetRole || 'General',
                max_recommendations: vm.maxRecommendations
            };

            $log.debug('RecommendationsDisplay: Loading recommendations with data:', requestData);

            ApiService.post('/recommendations', requestData)
                .then(function(response) {
                    if (response && response.recommendations) {
                        vm.recommendations = response.recommendations;
                        $log.debug('RecommendationsDisplay: Loaded recommendations:', vm.recommendations);
                    } else {
                        vm.recommendations = [];
                        $log.warn('RecommendationsDisplay: No recommendations in response');
                    }
                })
                .catch(function(error) {
                    vm.error = 'Failed to load recommendations';
                    vm.recommendations = [];
                    $log.error('RecommendationsDisplay: Error loading recommendations:', error);
                    
                    // Load fallback recommendations
                    loadFallbackRecommendations();
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        /**
         * Load fallback recommendations when API fails
         */
        function loadFallbackRecommendations() {
            vm.recommendations = [
                {
                    id: 'fallback-1',
                    title: 'Interview Preparation Basics',
                    description: 'Learn fundamental interview skills and techniques',
                    type: 'course',
                    provider: 'Internal',
                    url: '#',
                    duration: 30,
                    difficulty: 'beginner',
                    tags: ['interview-skills', 'basics']
                },
                {
                    id: 'fallback-2',
                    title: 'Behavioral Interview Questions',
                    description: 'Master the STAR method for behavioral questions',
                    type: 'video',
                    provider: 'Internal',
                    url: '#',
                    duration: 15,
                    difficulty: 'intermediate',
                    tags: ['behavioral', 'star-method']
                }
            ];
        }

        /**
         * Track recommendation click
         */
        function trackClick(recommendation) {
            if (!recommendation || !recommendation.id) {
                return;
            }

            $log.debug('RecommendationsDisplay: Tracking click for recommendation:', recommendation.id);

            // Track click via API
            ApiService.post('/recommendations/' + recommendation.id + '/track', {
                action: 'click',
                timestamp: new Date().toISOString()
            })
                .then(function() {
                    $log.debug('RecommendationsDisplay: Click tracked successfully');
                })
                .catch(function(error) {
                    $log.error('RecommendationsDisplay: Error tracking click:', error);
                });

            // Notify parent component
            if (vm.onRecommendationClick) {
                vm.onRecommendationClick({ recommendation: recommendation });
            }

            // Open recommendation URL
            if (recommendation.url && recommendation.url !== '#') {
                window.open(recommendation.url, '_blank');
            }
        }

        /**
         * Submit user feedback for recommendation
         */
        function submitFeedback(recommendation, feedbackType) {
            if (!recommendation || !recommendation.id) {
                return;
            }

            $log.debug('RecommendationsDisplay: Submitting feedback:', feedbackType, 'for:', recommendation.id);

            var feedbackData = {
                feedback_type: feedbackType,
                timestamp: new Date().toISOString()
            };

            ApiService.post('/recommendations/' + recommendation.id + '/feedback', feedbackData)
                .then(function() {
                    vm.feedbackSubmitted[recommendation.id] = feedbackType;
                    $log.debug('RecommendationsDisplay: Feedback submitted successfully');
                    
                    // Notify parent component
                    if (vm.onFeedback) {
                        vm.onFeedback({ 
                            recommendation: recommendation, 
                            feedback: feedbackType 
                        });
                    }
                })
                .catch(function(error) {
                    $log.error('RecommendationsDisplay: Error submitting feedback:', error);
                });
        }

        /**
         * Get icon for recommendation type
         */
        function getRecommendationIcon(type) {
            var icons = {
                'video': 'fas fa-play-circle',
                'course': 'fas fa-graduation-cap',
                'article': 'fas fa-newspaper',
                'book': 'fas fa-book',
                'tutorial': 'fas fa-code',
                'practice': 'fas fa-dumbbell'
            };
            
            return icons[type] || 'fas fa-bookmark';
        }

        /**
         * Get CSS class for provider badge
         */
        function getProviderBadgeClass(provider) {
            var classes = {
                'YouTube': 'bg-danger',
                'Coursera': 'bg-primary',
                'Udemy': 'bg-warning',
                'LinkedIn Learning': 'bg-info',
                'Internal': 'bg-success'
            };
            
            return classes[provider] || 'bg-secondary';
        }

        /**
         * Format duration in minutes to readable format
         */
        function formatDuration(minutes) {
            if (!minutes) return 'N/A';
            
            if (minutes < 60) {
                return minutes + ' min';
            } else {
                var hours = Math.floor(minutes / 60);
                var remainingMinutes = minutes % 60;
                
                if (remainingMinutes === 0) {
                    return hours + 'h';
                } else {
                    return hours + 'h ' + remainingMinutes + 'm';
                }
            }
        }
    }
})();