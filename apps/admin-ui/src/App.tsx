import React, { useState } from 'react';
import { 
  BarChart3, 
  Database, 
  Globe, 
  Play, 
  Search, 
  Settings,
  Users,
  FileText,
  Zap,
  TrendingUp,
  Clock,
  CheckCircle
} from 'lucide-react';
import { clsx } from 'clsx';

interface NavItem {
  name: string;
  icon: React.ReactNode;
  current: boolean;
}

interface LanguageCompleteness {
  language: string;
  dialect: string;
  minutes: number;
  targetMinutes: number;
  phonemeCoverage: number;
  status: 'complete' | 'in-progress' | 'pending';
}

interface SeekerJob {
  id: string;
  language: string;
  dialect: string;
  type: 'phoneme-gap' | 'dialect-balance' | 'topic-coverage';
  status: 'running' | 'queued' | 'completed' | 'failed';
  progress: number;
  createdAt: string;
}

const mockLanguages: LanguageCompleteness[] = [
  {
    language: 'English',
    dialect: 'US',
    minutes: 1247,
    targetMinutes: 1500,
    phonemeCoverage: 0.92,
    status: 'in-progress'
  },
  {
    language: 'Spanish',
    dialect: 'ES',
    minutes: 890,
    targetMinutes: 1200,
    phonemeCoverage: 0.87,
    status: 'in-progress'
  },
  {
    language: 'French',
    dialect: 'FR',
    minutes: 1534,
    targetMinutes: 1200,
    phonemeCoverage: 0.96,
    status: 'complete'
  }
];

const mockSeekerJobs: SeekerJob[] = [
  {
    id: 'job-1',
    language: 'English',
    dialect: 'US',
    type: 'phoneme-gap',
    status: 'running',
    progress: 67,
    createdAt: '2025-01-15T10:30:00Z'
  },
  {
    id: 'job-2',
    language: 'Spanish',
    dialect: 'ES',
    type: 'dialect-balance',
    status: 'completed',
    progress: 100,
    createdAt: '2025-01-15T09:15:00Z'
  }
];

function App() {
  const [currentTab, setCurrentTab] = useState('overview');

  const navigation: NavItem[] = [
    { name: 'Overview', icon: <BarChart3 className="w-5 h-5" />, current: currentTab === 'overview' },
    { name: 'Languages', icon: <Globe className="w-5 h-5" />, current: currentTab === 'languages' },
    { name: 'Seekers', icon: <Search className="w-5 h-5" />, current: currentTab === 'seekers' },
    { name: 'Batches', icon: <Database className="w-5 h-5" />, current: currentTab === 'batches' },
    { name: 'Settings', icon: <Settings className="w-5 h-5" />, current: currentTab === 'settings' },
  ];

  const getStatusBadge = (status: string) => {
    const baseClasses = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium";
    switch (status) {
      case 'complete':
      case 'completed':
        return `${baseClasses} bg-green-100 text-green-800`;
      case 'in-progress':
      case 'running':
        return `${baseClasses} bg-blue-100 text-blue-800`;
      case 'pending':
      case 'queued':
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      case 'failed':
        return `${baseClasses} bg-red-100 text-red-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

  const renderOverviewTab = () => (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Globe className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Languages
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {mockLanguages.length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Clock className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Minutes
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {mockLanguages.reduce((acc, lang) => acc + lang.minutes, 0).toLocaleString()}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Zap className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Active Seekers
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {mockSeekerJobs.filter(job => job.status === 'running').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <TrendingUp className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Avg Coverage
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {Math.round(mockLanguages.reduce((acc, lang) => acc + lang.phonemeCoverage, 0) / mockLanguages.length * 100)}%
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Recent Activity
          </h3>
          <div className="mt-5">
            <div className="flow-root">
              <ul className="-mb-8">
                {mockSeekerJobs.slice(0, 3).map((job, idx) => (
                  <li key={job.id}>
                    <div className="relative pb-8">
                      {idx !== mockSeekerJobs.slice(0, 3).length - 1 && (
                        <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true" />
                      )}
                      <div className="relative flex space-x-3">
                        <div>
                          <span className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center ring-8 ring-white">
                            <Search className="w-4 h-4 text-white" />
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div>
                            <p className="text-sm text-gray-500">
                              Seeker job for <span className="font-medium text-gray-900">{job.language} ({job.dialect})</span>
                            </p>
                            <p className="mt-0.5 text-xs text-gray-400">
                              {new Date(job.createdAt).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderLanguagesTab = () => (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
          Language Completeness
        </h3>
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Language
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Minutes
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Phoneme Coverage
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {mockLanguages.map((lang) => (
                <tr key={`${lang.language}-${lang.dialect}`}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {lang.language}
                        </div>
                        <div className="text-sm text-gray-500">
                          {lang.dialect}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {lang.minutes.toLocaleString()} / {lang.targetMinutes.toLocaleString()}
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `${Math.min(100, (lang.minutes / lang.targetMinutes) * 100)}%` }}
                      ></div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {Math.round(lang.phonemeCoverage * 100)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={getStatusBadge(lang.status)}>
                      {lang.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderSeekersTab = () => (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Seeker Jobs
            </h3>
            <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
              <Play className="w-4 h-4 mr-2" />
              Start New Seeker
        </button>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Language
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Progress
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {mockSeekerJobs.map((job) => (
                  <tr key={job.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {job.language}
                      </div>
                      <div className="text-sm text-gray-500">
                        {job.dialect}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {job.type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                          <div 
                            className="bg-green-600 h-2 rounded-full" 
                            style={{ width: `${job.progress}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-900">{job.progress}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={getStatusBadge(job.status)}>
                        {job.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(job.createdAt).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );

  const renderBatchesTab = () => (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
          Processing Batches
        </h3>
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No batches</h3>
          <p className="mt-1 text-sm text-gray-500">
            Get started by uploading a new batch for processing.
          </p>
          <div className="mt-6">
            <button className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
              <Database className="w-4 h-4 mr-2" />
              Upload Batch
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderCurrentTab = () => {
    switch (currentTab) {
      case 'overview':
        return renderOverviewTab();
      case 'languages':
        return renderLanguagesTab();
      case 'seekers':
        return renderSeekersTab();
      case 'batches':
        return renderBatchesTab();
      case 'settings':
        return (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Settings
              </h3>
              <p className="text-sm text-gray-500">
                Application settings and configuration options will be available here.
              </p>
            </div>
          </div>
        );
      default:
        return renderOverviewTab();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex">
        {/* Sidebar */}
        <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
          <div className="flex-1 flex flex-col min-h-0 bg-white shadow">
            <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
              <div className="flex items-center flex-shrink-0 px-4">
                <h1 className="text-xl font-semibold text-gray-900">
                  Mumbl Admin
                </h1>
              </div>
              <nav className="mt-5 flex-1 px-2 space-y-1">
                {navigation.map((item) => (
                  <button
                    key={item.name}
                    onClick={() => setCurrentTab(item.name.toLowerCase())}
                    className={clsx(
                      item.current
                        ? 'bg-primary-100 border-primary-500 text-primary-700'
                        : 'border-transparent text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                      'group w-full flex items-center pl-2 pr-2 py-2 border-l-4 text-sm font-medium'
                    )}
                  >
                    {item.icon}
                    <span className="ml-3">{item.name}</span>
                  </button>
                ))}
              </nav>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="md:pl-64 flex flex-col flex-1">
          <main className="flex-1">
            <div className="py-6">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                <h1 className="text-2xl font-semibold text-gray-900 capitalize">
                  {currentTab}
                </h1>
              </div>
              <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                <div className="py-4">
                  {renderCurrentTab()}
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;