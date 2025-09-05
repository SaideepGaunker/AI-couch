/**
 * Role Hierarchy Service for managing role data from API
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('RoleHierarchyService', RoleHierarchyService);

    RoleHierarchyService.$inject = ['ApiService', '$q', '$log'];

    function RoleHierarchyService(ApiService, $q, $log) {
        var service = {
            getRoleHierarchy: getRoleHierarchy,
            getMainRoles: getMainRoles,
            getSubRoles: getSubRoles,
            getSpecializations: getSpecializations,
            getTechStacks: getTechStacks,
            updateUserRole: updateUserRole,
            // Cache management
            clearCache: clearCache,
            _cache: {}
        };

        return service;

        /**
         * Get complete role hierarchy structure
         */
        function getRoleHierarchy() {
            $log.debug('RoleHierarchyService: Getting role hierarchy');
            
            // Check cache first
            if (service._cache.hierarchy) {
                $log.debug('RoleHierarchyService: Returning cached hierarchy');
                return $q.resolve(service._cache.hierarchy);
            }

            return ApiService.get('/roles/hierarchy')
                .then(function(data) {
                    // Cache the result
                    service._cache.hierarchy = data;
                    $log.debug('RoleHierarchyService: Cached role hierarchy with', Object.keys(data).length, 'main roles');
                    return data;
                })
                .catch(function(error) {
                    $log.error('RoleHierarchyService: Error getting role hierarchy', error);
                    
                    // Return fallback static data if API fails
                    var fallbackData = getFallbackRoleHierarchy();
                    service._cache.hierarchy = fallbackData;
                    return fallbackData;
                });
        }

        /**
         * Get list of main roles
         */
        function getMainRoles() {
            $log.debug('RoleHierarchyService: Getting main roles');
            
            return ApiService.get('/roles/main-roles')
                .then(function(data) {
                    $log.debug('RoleHierarchyService: Retrieved', data.length, 'main roles');
                    return data;
                })
                .catch(function(error) {
                    $log.error('RoleHierarchyService: Error getting main roles', error);
                    
                    // Fallback to extracting from cached hierarchy
                    if (service._cache.hierarchy) {
                        return Object.keys(service._cache.hierarchy);
                    }
                    
                    return [];
                });
        }

        /**
         * Get sub roles for a specific main role
         */
        function getSubRoles(mainRole) {
            $log.debug('RoleHierarchyService: Getting sub roles for', mainRole);
            
            if (!mainRole) {
                return $q.resolve([]);
            }

            return ApiService.get('/roles/sub-roles/' + encodeURIComponent(mainRole))
                .then(function(data) {
                    $log.debug('RoleHierarchyService: Retrieved', data.length, 'sub roles for', mainRole);
                    return data;
                })
                .catch(function(error) {
                    $log.error('RoleHierarchyService: Error getting sub roles', error);
                    
                    // Fallback to extracting from cached hierarchy
                    if (service._cache.hierarchy && service._cache.hierarchy[mainRole]) {
                        return Object.keys(service._cache.hierarchy[mainRole]);
                    }
                    
                    return [];
                });
        }

        /**
         * Get specializations for a specific main role and sub role
         */
        function getSpecializations(mainRole, subRole) {
            $log.debug('RoleHierarchyService: Getting specializations for', mainRole, '/', subRole);
            
            if (!mainRole) {
                return $q.resolve([]);
            }

            var params = {};
            if (subRole) {
                params.sub_role = subRole;
            }

            return ApiService.get('/roles/specializations/' + encodeURIComponent(mainRole), params)
                .then(function(data) {
                    $log.debug('RoleHierarchyService: Retrieved', data.length, 'specializations');
                    return data;
                })
                .catch(function(error) {
                    $log.error('RoleHierarchyService: Error getting specializations', error);
                    
                    // Fallback to extracting from cached hierarchy
                    if (service._cache.hierarchy && 
                        service._cache.hierarchy[mainRole] && 
                        service._cache.hierarchy[mainRole][subRole] &&
                        service._cache.hierarchy[mainRole][subRole].specializations) {
                        return service._cache.hierarchy[mainRole][subRole].specializations;
                    }
                    
                    return [];
                });
        }

        /**
         * Get tech stacks for a specific main role and optionally sub role
         */
        function getTechStacks(mainRole, subRole) {
            $log.debug('RoleHierarchyService: Getting tech stacks for', mainRole, '/', subRole);
            
            if (!mainRole) {
                return $q.resolve([]);
            }

            var params = {};
            if (subRole) {
                params.sub_role = subRole;
            }

            return ApiService.get('/roles/tech-stacks/' + encodeURIComponent(mainRole), params)
                .then(function(data) {
                    $log.debug('RoleHierarchyService: Retrieved', data.length, 'tech stacks');
                    return data;
                })
                .catch(function(error) {
                    $log.error('RoleHierarchyService: Error getting tech stacks', error);
                    
                    // Fallback to extracting from cached hierarchy
                    if (service._cache.hierarchy && 
                        service._cache.hierarchy[mainRole] && 
                        service._cache.hierarchy[mainRole][subRole] &&
                        service._cache.hierarchy[mainRole][subRole].tech_stacks) {
                        return service._cache.hierarchy[mainRole][subRole].tech_stacks;
                    }
                    
                    return [];
                });
        }

        /**
         * Update user's role information
         */
        function updateUserRole(roleData) {
            $log.debug('RoleHierarchyService: Updating user role', roleData);
            
            return ApiService.put('/roles/user/role', roleData)
                .then(function(response) {
                    $log.debug('RoleHierarchyService: User role updated successfully');
                    return response;
                })
                .catch(function(error) {
                    $log.error('RoleHierarchyService: Error updating user role', error);
                    throw error;
                });
        }

        /**
         * Clear cached data
         */
        function clearCache() {
            service._cache = {};
            $log.debug('RoleHierarchyService: Cache cleared');
        }

        /**
         * Fallback role hierarchy data for when API is unavailable
         */
        function getFallbackRoleHierarchy() {
            return {
                'Software Developer': {
                    'Frontend Developer': {
                        specializations: ['React Developer', 'Angular Developer', 'Vue.js Developer'],
                        tech_stacks: ['React', 'Angular', 'Vue.js', 'JavaScript', 'TypeScript', 'HTML', 'CSS']
                    },
                    'Backend Developer': {
                        specializations: ['Node.js Developer', 'Python Developer', 'Rust Developer'],
                        tech_stacks: ['Node.js', 'Python', 'Rust', 'Java', 'Express.js', 'Django', 'Flask']
                    },
                    'Mobile Developer': {
                        specializations: ['iOS Developer', 'Android Developer', 'React Native Developer'],
                        tech_stacks: ['Swift', 'Kotlin', 'React Native', 'Flutter', 'Xamarin']
                    },
                    'Full Stack Developer': {
                        specializations: ['MEAN Stack', 'MERN Stack', 'Django Full Stack'],
                        tech_stacks: ['React', 'Node.js', 'Python', 'MongoDB', 'PostgreSQL']
                    }
                },
                'Data Scientist': {
                    'ML Engineer': {
                        specializations: ['Computer Vision Engineer', 'NLP Specialist', 'Deep Learning'],
                        tech_stacks: ['Python', 'TensorFlow', 'PyTorch', 'Scikit-learn', 'OpenCV']
                    },
                    'Data Analyst': {
                        specializations: ['Business Intelligence Analyst', 'Financial Analyst'],
                        tech_stacks: ['Python', 'R', 'SQL', 'Tableau', 'Power BI']
                    },
                    'AI Researcher': {
                        specializations: ['Research Scientist', 'Algorithm Developer'],
                        tech_stacks: ['Python', 'PyTorch', 'TensorFlow', 'Jupyter', 'CUDA']
                    },
                    'Data Engineer': {
                        specializations: ['Big Data Engineer', 'ETL Developer'],
                        tech_stacks: ['Apache Spark', 'Hadoop', 'Kafka', 'Python', 'Scala']
                    }
                },
                'Product Manager': {
                    'Technical Product Manager': {
                        specializations: ['API Product Manager', 'Platform PM'],
                        tech_stacks: ['Jira', 'Confluence', 'Figma', 'SQL', 'Python']
                    },
                    'Growth Product Manager': {
                        specializations: ['User Acquisition PM', 'Retention PM'],
                        tech_stacks: ['Amplitude', 'Mixpanel', 'Google Analytics', 'A/B Testing', 'SQL']
                    },
                    'Consumer Product Manager': {
                        specializations: ['Mobile Product Manager', 'Web Product Manager'],
                        tech_stacks: ['Figma', 'App Store Connect', 'Firebase', 'Amplitude', 'UserVoice']
                    }
                },
                'DevOps Engineer': {
                    'Site Reliability Engineer': {
                        specializations: ['Platform SRE', 'Infrastructure SRE'],
                        tech_stacks: ['Kubernetes', 'Docker', 'Prometheus', 'Grafana', 'Terraform']
                    },
                    'Cloud Engineer': {
                        specializations: ['AWS Solutions Architect', 'Azure DevOps Engineer'],
                        tech_stacks: ['AWS', 'Azure', 'Terraform', 'CloudFormation', 'Docker']
                    },
                    'Security Engineer': {
                        specializations: ['DevSecOps Engineer', 'Application Security'],
                        tech_stacks: ['Docker', 'Kubernetes', 'Vault', 'SAST Tools', 'DAST Tools']
                    }
                }
            };
        }
    }
})();