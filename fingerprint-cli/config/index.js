const config = {
  development: {
    database: {
      host: 'localhost',
      user: 'root',
      password: '',
      database: 'fpsnsdb'
    },
    api: {
      baseUrl: 'http://localhost:80'
    }
  },
  production: {
    database: {
      connectionString: process.env.DATABASE_URL || 'postgresql://neondb_owner:npg_hnBPkldL2W9i@ep-raspy-base-akq29c7r.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require'
    },
    api: {
      baseUrl: process.env.API_URL || 'https://fingerprint-system-sns.vercel.app'
    }
  }
};

const env = process.env.NODE_ENV || 'development';
module.exports = config[env];
