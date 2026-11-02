This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

`npm run dev` serves on [http://localhost:3001](http://localhost:3001). The Docker `geopolitics_frontend` container also binds 3001, so while the stack is up, run a second dev server (a worktree, a prototype) with `npx next dev --port 3002`.

A git worktree that symlinks `node_modules` from the main checkout fails under Turbopack ("Symlink node_modules is invalid, it points out of the filesystem root"). Run it with `next dev --webpack`, or `npm ci` inside the worktree.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
