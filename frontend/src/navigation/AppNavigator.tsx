/**
 * App Navigator
 * Main app navigation with bottom tabs
 */

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import ProjectsScreen from '@/screens/projects/ProjectsScreen';
import ProjectDetailScreen from '@/screens/projects/ProjectDetailScreen';
import IssuesScreen from '@/screens/issues/IssuesScreen';
import IssueDetailScreen from '@/screens/issues/IssueDetailScreen';
import BoardsScreen from '@/screens/boards/BoardsScreen';
import ProfileScreen from '@/screens/profile/ProfileScreen';

export type ProjectsStackParamList = {
  ProjectsList: undefined;
  ProjectDetail: { projectId: string };
};

export type IssuesStackParamList = {
  IssuesList: undefined;
  IssueDetail: { issueId: string };
};

export type BoardsStackParamList = {
  BoardsList: undefined;
};

export type ProfileStackParamList = {
  ProfileMain: undefined;
};

const Tab = createBottomTabNavigator();
const ProjectsStack = createStackNavigator<ProjectsStackParamList>();
const IssuesStack = createStackNavigator<IssuesStackParamList>();
const BoardsStack = createStackNavigator<BoardsStackParamList>();
const ProfileStack = createStackNavigator<ProfileStackParamList>();

// Projects Stack Navigator
const ProjectsNavigator: React.FC = () => {
  return (
    <ProjectsStack.Navigator>
      <ProjectsStack.Screen
        name="ProjectsList"
        component={ProjectsScreen}
        options={{ title: 'Projects' }}
      />
      <ProjectsStack.Screen
        name="ProjectDetail"
        component={ProjectDetailScreen}
        options={{ title: 'Project Details' }}
      />
    </ProjectsStack.Navigator>
  );
};

// Issues Stack Navigator
const IssuesNavigator: React.FC = () => {
  return (
    <IssuesStack.Navigator>
      <IssuesStack.Screen
        name="IssuesList"
        component={IssuesScreen}
        options={{ title: 'Issues' }}
      />
      <IssuesStack.Screen
        name="IssueDetail"
        component={IssueDetailScreen}
        options={{ title: 'Issue Details' }}
      />
    </IssuesStack.Navigator>
  );
};

// Boards Stack Navigator
const BoardsNavigator: React.FC = () => {
  return (
    <BoardsStack.Navigator>
      <BoardsStack.Screen
        name="BoardsList"
        component={BoardsScreen}
        options={{ title: 'Boards' }}
      />
    </BoardsStack.Navigator>
  );
};

// Profile Stack Navigator
const ProfileNavigator: React.FC = () => {
  return (
    <ProfileStack.Navigator>
      <ProfileStack.Screen
        name="ProfileMain"
        component={ProfileScreen}
        options={{ title: 'Profile' }}
      />
    </ProfileStack.Navigator>
  );
};

// Main App Navigator with Bottom Tabs
const AppNavigator: React.FC = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: string;

          if (route.name === 'Projects') {
            iconName = focused ? 'folder' : 'folder-outline';
          } else if (route.name === 'Issues') {
            iconName = focused ? 'bug' : 'bug-outline';
          } else if (route.name === 'Boards') {
            iconName = focused ? 'view-dashboard' : 'view-dashboard-outline';
          } else if (route.name === 'Profile') {
            iconName = focused ? 'account' : 'account-outline';
          } else {
            iconName = 'help';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#2196F3',
        tabBarInactiveTintColor: '#757575',
      })}
    >
      <Tab.Screen name="Projects" component={ProjectsNavigator} />
      <Tab.Screen name="Issues" component={IssuesNavigator} />
      <Tab.Screen name="Boards" component={BoardsNavigator} />
      <Tab.Screen name="Profile" component={ProfileNavigator} />
    </Tab.Navigator>
  );
};

export default AppNavigator;
