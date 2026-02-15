# BugsTracker Mobile

Production-grade React Native mobile app for BugsTracker issue tracking system.

## Features

- 📱 **Cross-platform** - iOS and Android support
- 🔐 **JWT Authentication** - Secure token-based auth with auto-refresh
- 🎨 **Material Design** - React Native Paper components
- ⚡ **Performance** - React Query caching and optimistic updates
- 🌐 **Offline Support** - AsyncStorage for offline data
- 🔄 **Real-time** - WebSocket integration for live updates
- 📊 **State Management** - Zustand for global state
- 🎯 **TypeScript** - Full type safety

## Tech Stack

- **Framework**: React Native (Expo)
- **Language**: TypeScript
- **Navigation**: React Navigation
- **State Management**: Zustand
- **Data Fetching**: React Query (TanStack Query)
- **UI Library**: React Native Paper
- **Forms**: React Hook Form
- **API Client**: Axios
- **Real-time**: Socket.IO Client

## Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0
- Expo CLI: `npm install -g expo-cli`
- iOS: Xcode (Mac only)
- Android: Android Studio

## Installation

```bash
# Install dependencies
npm install

# Start development server
npm start

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android

# Run on web
npm run web
```

## Project Structure

```
frontend/
├── src/
│   ├── api/                 # API clients
│   │   ├── client.ts       # Axios instance with interceptors
│   │   ├── auth.ts         # Authentication API
│   │   ├── issues.ts       # Issues API
│   │   └── projects.ts     # Projects API
│   │
│   ├── store/              # Zustand stores
│   │   ├── authStore.ts    # Authentication state
│   │   ├── issueStore.ts   # Issues state
│   │   └── projectStore.ts # Projects state
│   │
│   ├── navigation/         # Navigation structure
│   │   ├── RootNavigator.tsx
│   │   ├── AuthNavigator.tsx
│   │   └── AppNavigator.tsx
│   │
│   ├── screens/            # Screen components
│   │   ├── auth/           # Login, Register
│   │   ├── projects/       # Project list, detail
│   │   ├── issues/         # Issue list, detail
│   │   ├── boards/         # Kanban/Scrum boards
│   │   └── profile/        # User profile
│   │
│   ├── components/         # Reusable components
│   │   ├── common/         # Buttons, inputs, etc.
│   │   ├── issues/         # Issue cards, filters
│   │   └── projects/       # Project cards
│   │
│   ├── hooks/              # Custom hooks
│   │   ├── useAuth.ts      # Authentication hook
│   │   ├── useIssues.ts    # Issues data hook
│   │   └── useProjects.ts  # Projects data hook
│   │
│   ├── types/              # TypeScript types
│   │   ├── auth.ts
│   │   ├── issue.ts
│   │   └── project.ts
│   │
│   ├── utils/              # Utilities
│   │   ├── validation.ts   # Form validation
│   │   └── formatting.ts   # Data formatting
│   │
│   └── config/             # Configuration
│       └── constants.ts    # App constants
│
├── App.tsx                 # App entry point
├── package.json            # Dependencies
└── tsconfig.json           # TypeScript config
```

## Configuration

Create a `.env` file in the root directory:

```bash
EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1
EXPO_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Scripts

```bash
# Development
npm start                    # Start Expo dev server
npm run android             # Run on Android
npm run ios                 # Run on iOS
npm run web                 # Run on web

# Testing
npm test                    # Run tests in watch mode
npm run test:ci             # Run tests once with coverage

# Code Quality
npm run lint                # Run ESLint
npm run lint:fix            # Fix ESLint errors
npm run type-check          # Run TypeScript compiler
npm run format              # Format code with Prettier
```

## API Integration

### Authentication

```typescript
import { useAuthStore } from '@/store/authStore';

const LoginScreen = () => {
  const { login, isLoading } = useAuthStore();

  const handleLogin = async () => {
    await login({ email, password });
  };
};
```

### Fetching Data with React Query

```typescript
import { useQuery } from '@tanstack/react-query';
import { issuesApi } from '@/api/issues';

const IssuesScreen = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['issues'],
    queryFn: () => issuesApi.list(),
  });
};
```

### Creating Issues

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { issuesApi } from '@/api/issues';

const CreateIssueScreen = () => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: issuesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
    },
  });

  const handleCreate = (data) => {
    mutation.mutate(data);
  };
};
```

## State Management

### Zustand Store Example

```typescript
import { create } from 'zustand';

interface IssueStore {
  filters: IssueFilters;
  setFilters: (filters: IssueFilters) => void;
}

export const useIssueStore = create<IssueStore>((set) => ({
  filters: {},
  setFilters: (filters) => set({ filters }),
}));
```

## Navigation

```typescript
import { useNavigation } from '@react-navigation/native';

const IssuesScreen = () => {
  const navigation = useNavigation();

  const handleIssuePress = (issueId: string) => {
    navigation.navigate('IssueDetail', { issueId });
  };
};
```

## Real-time Updates

WebSocket integration for live updates:

```typescript
import io from 'socket.io-client';
import { WS_BASE_URL } from '@/config/constants';

const socket = io(WS_BASE_URL, {
  auth: {
    token: accessToken,
  },
});

socket.on('issue.updated', (data) => {
  // Handle issue update
  queryClient.invalidateQueries({ queryKey: ['issues', data.id] });
});
```

## Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:ci

# Run specific test file
npm test -- IssueCard.test.tsx
```

## Building for Production

### iOS

```bash
# Build iOS app
expo build:ios

# Submit to App Store
expo upload:ios
```

### Android

```bash
# Build Android APK
expo build:android -t apk

# Build Android App Bundle
expo build:android -t app-bundle

# Submit to Play Store
expo upload:android
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EXPO_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000/api/v1` |
| `EXPO_PUBLIC_WS_URL` | WebSocket URL | `ws://localhost:8000/ws` |

## Troubleshooting

### Metro bundler issues

```bash
# Clear cache
npx expo start -c
```

### iOS build issues

```bash
# Clear iOS build
rm -rf ios/build
pod install --repo-update
```

### Android build issues

```bash
# Clean Android build
cd android
./gradlew clean
```

## Contributing

1. Follow TypeScript best practices
2. Write tests for new features
3. Run linter before committing
4. Use conventional commits

## Performance Optimization

- React Query caching (5-60 min)
- Optimistic UI updates
- Image lazy loading
- List virtualization (FlatList)
- Memoization (React.memo, useMemo)
- Code splitting (lazy loading)

## Security

- JWT tokens stored in SecureStore
- Auto token refresh
- HTTPS only in production
- Input validation
- XSS prevention
- Rate limiting

## License

Proprietary

## Support

- Email: support@bugstracker.com
- Documentation: https://docs.bugstracker.com
