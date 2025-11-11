import React from 'react';
import { Container, RadioGroup, Header, SpaceBetween } from '@cloudscape-design/components';

export default function FrameworkSelector({ value, onChange }) {
  return (
    <Container header={<Header variant="h3">Framework</Header>}>
      <RadioGroup
        value={value}
        onChange={({ detail }) => onChange(detail.value)}
        items={[
          {
            value: 'ray',
            label: 'Ray',
            description: 'Distributed Python framework'
          },
          {
            value: 'spark',
            label: 'Spark',
            description: 'Apache Spark on Lambda/EMR'
          }
        ]}
      />
    </Container>
  );
}
