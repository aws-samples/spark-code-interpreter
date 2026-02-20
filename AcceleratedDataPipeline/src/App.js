import '@cloudscape-design/global-styles/index.css';
import {
  AppLayout,
  Header,
  Container,
  ContentLayout,
  SideNavigation,
  TopNavigation,
  SpaceBetween,
  Modal,
  Box,
  FormField,
  Input,
  Button
} from '@cloudscape-design/components';
import { useState, useEffect } from 'react';
import AddBlueprintForm from './AddBlueprintForm';
import EditBlueprintForm from './EditBlueprintForm';
import CreateToolForm from './CreateToolForm';
import ManageToolForm from './ManageToolForm';
import SemanticSearchForm from './SemanticSearchForm';
import OnboardLambda from './OnboardLambda';
import OnboardRestAPI from './OnboardRestAPI';
import ArtifactsSection from './ArtifactsSection';
import { suppressResizeObserverErrors } from './utils/resizeObserverFix';

// Initialize global ResizeObserver error suppression
suppressResizeObserverErrors();

function App() {
  const [activeHref, setActiveHref] = useState('/');
  const [showAddBlueprint, setShowAddBlueprint] = useState(false);
  const [showEditBlueprint, setShowEditBlueprint] = useState(false);
  const [showCreateTool, setShowCreateTool] = useState(false);
  const [showManageTool, setShowManageTool] = useState(false);
  const [showSemanticSearch, setShowSemanticSearch] = useState(false);
  const [showOnboardLambda, setShowOnboardLambda] = useState(false);
  const [showOnboardRestAPI, setShowOnboardRestAPI] = useState(false);
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [showCredentialModal, setShowCredentialModal] = useState(false);
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const savedCredentials = localStorage.getItem('adapt-credentials');
    if (savedCredentials) {
      setCredentials(JSON.parse(savedCredentials));
    } else {
      setShowCredentialModal(true);
    }
  }, []);

  const handleCredentialSave = () => {
    localStorage.setItem('adapt-credentials', JSON.stringify(credentials));
    setShowCredentialModal(false);
  };

  return (
    <>
      <TopNavigation
        identity={{
          href: "#",
          title: "A-DAPT"
        }}
        utilities={[
          {
            type: "button",
            text: "Help",
            href: "#/help",
            external: false
          },
          {
            type: "menu-dropdown",
            text: "Profile",
            description: "user@example.com",
            iconName: "user-profile",
            onItemClick: ({ detail }) => {
              if (detail.id === 'credentials') {
                setShowCredentialModal(true);
              }
            },
            items: [
              { id: "profile", text: "Profile" },
              { id: "preferences", text: "Preferences" },
              { id: "credentials", text: "Configure Credentials" },
              { id: "signout", text: "Sign out" }
            ]
          }
        ]}
      />
      <AppLayout
        navigation={
          <SideNavigation
            activeHref={activeHref}
            header={{ href: "/", text: "Navigation" }}
            onFollow={event => {
              if (!event.detail.external) {
                event.preventDefault();
                setActiveHref(event.detail.href);
                if (event.detail.href === '#/blueprints/add') {
                  setShowAddBlueprint(true);
                  setShowEditBlueprint(false);
                  setShowCreateTool(false);
                  setShowManageTool(false);
                  setShowSemanticSearch(false);
                  setShowOnboardLambda(false);
                  setShowOnboardRestAPI(false);
                  setShowArtifacts(false);
                } else if (event.detail.href === '#/blueprints/edit') {
                  setShowEditBlueprint(true);
                  setShowAddBlueprint(false);
                  setShowCreateTool(false);
                  setShowManageTool(false);
                  setShowSemanticSearch(false);
                  setShowOnboardLambda(false);
                  setShowOnboardRestAPI(false);
                  setShowArtifacts(false);
                } else if (event.detail.href === '#/tools/create') {
                  setShowCreateTool(true);
                  setShowAddBlueprint(false);
                  setShowEditBlueprint(false);
                  setShowManageTool(false);
                  setShowSemanticSearch(false);
                  setShowOnboardLambda(false);
                  setShowOnboardRestAPI(false);
                  setShowArtifacts(false);
                } else if (event.detail.href === '#/tools/manage') {
                  setShowManageTool(true);
                  setShowAddBlueprint(false);
                  setShowEditBlueprint(false);
                  setShowCreateTool(false);
                  setShowSemanticSearch(false);
                  setShowOnboardLambda(false);
                  setShowOnboardRestAPI(false);
                  setShowArtifacts(false);
                } else if (event.detail.href === '#/deployment/agentic-core') {
                  setShowSemanticSearch(true);
                  setShowAddBlueprint(false);
                  setShowEditBlueprint(false);
                  setShowCreateTool(false);
                  setShowManageTool(false);
                  setShowOnboardLambda(false);
                  setShowOnboardRestAPI(false);
                  setShowArtifacts(false);
                } else if (event.detail.href === '#/onboard/lambda') {
                  setShowOnboardLambda(true);
                  setShowAddBlueprint(false);
                  setShowEditBlueprint(false);
                  setShowCreateTool(false);
                  setShowManageTool(false);
                  setShowSemanticSearch(false);
                  setShowOnboardRestAPI(false);
                  setShowArtifacts(false);
                } else if (event.detail.href === '#/onboard/restapi') {
                  setShowOnboardRestAPI(true);
                  setShowAddBlueprint(false);
                  setShowEditBlueprint(false);
                  setShowCreateTool(false);
                  setShowManageTool(false);
                  setShowSemanticSearch(false);
                  setShowOnboardLambda(false);
                  setShowArtifacts(false);
                } else if (event.detail.href === '#/artifacts') {
                  setShowArtifacts(true);
                  setShowAddBlueprint(false);
                  setShowEditBlueprint(false);
                  setShowCreateTool(false);
                  setShowManageTool(false);
                  setShowSemanticSearch(false);
                  setShowOnboardLambda(false);
                  setShowOnboardRestAPI(false);
                } else {
                  setShowAddBlueprint(false);
                  setShowEditBlueprint(false);
                  setShowCreateTool(false);
                  setShowManageTool(false);
                  setShowSemanticSearch(false);
                  setShowOnboardLambda(false);
                  setShowOnboardRestAPI(false);
                  setShowArtifacts(false);
                }
              }
            }}
            items={[
              {
                type: "section",
                text: "Blueprints",
                items: [
                  { type: "link", text: "Add Blueprint", href: "#/blueprints/add" },
                  { type: "link", text: "Manage Blueprint", href: "#/blueprints/edit" }
                ]
              },
              {
                type: "section",
                text: "Tools",
                items: [
                  { type: "link", text: "Create new Tools", href: "#/tools/create" },
                  { type: "link", text: "Manage Tools", href: "#/tools/manage" }
                ]
              },
              {
                type: "section",
                text: "Explore",
                items: [
                  { type: "link", text: "Semantic Search", href: "#/deployment/agentic-core" }
                ]
              },
              {
                type: "section",
                text: "Onboard",
                items: [
                  { type: "link", text: "Lambda", href: "#/onboard/lambda" },
                  { type: "link", text: "Rest API", href: "#/onboard/restapi" }
                ]
              },
              {
                type: "section",
                text: "Files",
                items: [
                  { type: "link", text: "Artifacts", href: "#/artifacts" }
                ]
              }
            ]}
          />
        }
        content={
          <ContentLayout header={<h1>Accelerated - Data Access Pipeline Tool</h1>}>
            {showAddBlueprint ? (
              <AddBlueprintForm onCancel={() => setShowAddBlueprint(false)} />
            ) : showEditBlueprint ? (
              <EditBlueprintForm onCancel={() => setShowEditBlueprint(false)} />
            ) : showCreateTool ? (
              <CreateToolForm onCancel={() => setShowCreateTool(false)} />
            ) : showManageTool ? (
              <ManageToolForm
                onCancel={() => setShowManageTool(false)}
                credentials={credentials}
              />
            ) : showSemanticSearch ? (
              <SemanticSearchForm
                onCancel={() => setShowSemanticSearch(false)}
                credentials={credentials}
              />
            ) : showOnboardLambda ? (
              <OnboardLambda
                onCancel={() => setShowOnboardLambda(false)}
                credentials={credentials}
              />
            ) : showOnboardRestAPI ? (
              <OnboardRestAPI 
                onCancel={() => setShowOnboardRestAPI(false)} 
                credentials={credentials}
              />
            ) : showArtifacts ? (
              <ArtifactsSection onCancel={() => setShowArtifacts(false)} />
            ) : (
              <Container>
                <SpaceBetween direction="vertical" size="l">
                  <p>A-DAPT (Accelerated - Data Access Pipeline Tool) enables rapid creation and deployment of AI agents with customizable data access capabilities.</p>
                  <p><strong>Blueprints:</strong> Create reusable templates that define AWS service integrations and data access patterns for standardized tool development.</p>
                  <p><strong>Tools:</strong> Generate executable functions from blueprints and manage them. Create, customize, and deploy as MCP servers or agents.</p>
                  <p><strong>Explore:</strong> Discover and deploy your tools as production-ready AI agents with real-time monitoring and scalable infrastructure on AWS.</p>
                  <p><strong>Artifacts:</strong> Upload and manage your presentation materials, documents, videos, and architecture images in one centralized location.</p>
                </SpaceBetween>
              </Container>
            )}
          </ContentLayout>
        }
      />

      <Modal
        visible={showCredentialModal}
        onDismiss={() => setShowCredentialModal(false)}
        header="Configure Credentials"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="primary"
                onClick={handleCredentialSave}
                disabled={!credentials.username || !credentials.password}
              >
                Save
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <FormField label="Username">
            <Input
              value={credentials.username}
              onChange={({ detail }) => setCredentials(prev => ({ ...prev, username: detail.value }))}
              placeholder="Enter username"
            />
          </FormField>
          <FormField label="Password">
            <div style={{ position: 'relative' }}>
              <Input
                value={credentials.password}
                onChange={({ detail }) => setCredentials(prev => ({ ...prev, password: detail.value }))}
                placeholder="Enter password"
                type={showPassword ? "text" : "password"}
              />
              <svg
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  cursor: 'pointer',
                  width: '20px',
                  height: '20px',
                  fill: '#545b64',
                  zIndex: 1
                }}
                title={showPassword ? "Hide password" : "Show password"}
                viewBox="0 0 24 24"
              >
                {showPassword ? (
                  <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" />
                ) : (
                  <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z" />
                )}
              </svg>
            </div>
          </FormField>
        </SpaceBetween>
      </Modal>

    </>
  );
}

export default App;