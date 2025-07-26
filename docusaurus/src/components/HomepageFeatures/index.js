import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Satellite Imagery Access',
    description: (
      <>
        Connect your AI applications to the SkyFi Platform's extensive satellite imagery archive. 
        Search, order, and analyze high-resolution satellite data with simple API calls through 
        the Model Context Protocol.
      </>
    ),
  },
  {
    title: 'Geospatial Intelligence',
    description: (
      <>
        Leverage OpenStreetMap integration for comprehensive geospatial analysis. 
        Perform geocoding, location search, and geometric operations to enhance 
        your satellite imagery workflows with contextual geographic data.
      </>
    ),
  },
  {
    title: 'AI-Native Integration',
    description: (
      <>
        Built specifically for AI applications using the Model Context Protocol. 
        Works seamlessly with Claude Desktop, Cursor, Windsurf, and VSCode to bring 
        satellite intelligence directly into your development workflow.
      </>
    ),
  },
];

function Feature({title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
