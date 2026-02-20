import boto3
import time

def get_codebuild_status(agent_name, connection_id, send_websocket_message):
    """Get CodeBuild project status and wait for success"""
    codebuild_client = boto3.client('codebuild')
    project_name = f'bedrock-agentcore-{agent_name}-builder'
    
    try:
        send_websocket_message(connection_id, {
            'status': 'CHECKING_CODEBUILD',
            'message': f'Checking CodeBuild project: {project_name}...'
        })
        
        # Get the most recent build ID for the project
        response = codebuild_client.list_builds_for_project(
            projectName=project_name, 
            sortOrder='DESCENDING', 
            limit=1
        )
        
        if response['ids']:
            build_id = response['ids'][0]
            
            # Loop until build succeeds or fails
            while True:
                build_details = codebuild_client.batch_get_builds(ids=[build_id])
                build_status = build_details['builds'][0]['buildStatus']
                
                send_websocket_message(connection_id, {
                    'status': 'CODEBUILD_STATUS',
                    'message': f'CodeBuild status: {build_status}',
                    'build_status': build_status,
                    'build_id': build_id
                })
                
                if build_status == 'SUCCEEDED':
                    send_websocket_message(connection_id, {
                        'status': 'CODEBUILD_COMPLETED',
                        'message': f'CodeBuild project {project_name} completed successfully!'
                    })
                    return build_status
                elif build_status in ['FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT']:
                    send_websocket_message(connection_id, {
                        'status': 'CODEBUILD_FAILED',
                        'message': f'CodeBuild project {project_name} failed with status: {build_status}'
                    })
                    return build_status
                
                # Wait 30 seconds before checking again
                time.sleep(30)
            
        else:
            send_websocket_message(connection_id, {
                'status': 'CODEBUILD_NOT_FOUND',
                'message': f'No builds found for project: {project_name}'
            })
            return None
            
    except Exception as e:
        send_websocket_message(connection_id, {
            'status': 'CODEBUILD_ERROR',
            'message': f'Error checking CodeBuild status: {str(e)}'
        })
        return None