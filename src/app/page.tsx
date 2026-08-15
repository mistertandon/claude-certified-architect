import { fetchPosts } from "@/lib/tmdb";
import type { Post } from "@/types/movie";
import PostCard from "@/components/post/PostCard";
import styles from "./page.module.scss";

export default async function HomePage() {
  let data: Post[] | null = null;
  let error: string | null = null;

  try {
    data = await fetchPosts();
  } catch {
    error = "Failed to load posts. Please try again later.";
  }

  return (
    <main className={styles.container}>
      <header className={styles.pageHeader}>
        <h1 className={styles.title}>Posts</h1>
        {data && (
          <span className={styles.resultCount}>
            {data.length} posts found
          </span>
        )}
      </header>

      {error && <p className={styles.error}>{error}</p>}

      {data && data.length === 0 && (
        <p className={styles.empty}>No posts found.</p>
      )}

      {data && data.length > 0 && (
        <div className={styles.grid}>
          {data.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </main>
  );
}
