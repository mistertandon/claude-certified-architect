import type { Post } from "@/types/movie";
import styles from "./PostCard.module.scss";

interface PostCardProps {
  post: Post;
}

export default function PostCard({ post }: PostCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.name}>{post.name}</h3>
      </div>
      <p className={styles.description}>{post.author}</p>
      <div className={styles.meta}>
        <span className={styles.metaItem}>{post.category}</span>
        <span className={styles.metaItem}>Rating: {post.rating}</span>
        <span className={styles.metaItem}>{post.lastUpdateTime}</span>
      </div>
    </div>
  );
}
