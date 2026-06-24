import numpy as np

def calculate_hit_ratio_at_k(recommendations: list, ground_truth: list, k: int = 10) -> float:
    """
    Hit Ratio @ K.
    recommendations: list of book IDs
    ground_truth: list of actual book IDs the user read/liked
    """
    if not ground_truth:
        return 0.0
    top_k_recs = set(recommendations[:k])
    hits = top_k_recs.intersection(set(ground_truth))
    return 1.0 if len(hits) > 0 else 0.0

def calculate_ndcg_at_k(recommendations: list, ground_truth: list, k: int = 10) -> float:
    """
    Normalized Discounted Cumulative Gain @ K.
    recommendations: list of book IDs
    ground_truth: list of actual book IDs the user read/liked
    """
    if not ground_truth:
        return 0.0
        
    top_k_recs = recommendations[:k]
    gt_set = set(ground_truth)
    
    dcg = 0.0
    for idx, item in enumerate(top_k_recs):
        if item in gt_set:
            dcg += 1.0 / np.log2(idx + 2)
            
    idcg = 0.0
    for idx in range(min(k, len(gt_set))):
        idcg += 1.0 / np.log2(idx + 2)
        
    if idcg == 0.0:
        return 0.0
    return dcg / idcg

def calculate_map_at_k(recommendations: list, ground_truth: list, k: int = 10) -> float:
    """
    Average Precision @ K.
    recommendations: list of book IDs
    ground_truth: list of actual book IDs the user read/liked
    """
    if not ground_truth:
        return 0.0
        
    top_k_recs = recommendations[:k]
    gt_set = set(ground_truth)
    
    avg_precision = 0.0
    hits = 0
    
    for idx, item in enumerate(top_k_recs):
        if item in gt_set:
            hits += 1
            avg_precision += hits / (idx + 1)
            
    if hits == 0:
        return 0.0
    return avg_precision / min(k, len(gt_set))

def calculate_catalog_coverage(all_recommendations: list, total_unique_books: int) -> float:
    """Percentage of catalog books recommended at least once."""
    if total_unique_books == 0:
        return 0.0
    unique_recommended = set(all_recommendations)
    return len(unique_recommended) / total_unique_books

def calculate_diversity(recommendations: list, book_embeddings_dict: dict) -> float:
    """
    Intra-List Diversity (ILD) based on embedding cosine distance.
    ILD = mean(1 - cosine_similarity(emb_i, emb_j))
    """
    if len(recommendations) < 2:
        return 0.0
        
    embs = []
    for item in recommendations:
        if item in book_embeddings_dict:
            embs.append(book_embeddings_dict[item])
            
    if len(embs) < 2:
        return 0.0
        
    embs = np.array(embs)
    # L2 normalize embeddings
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    norm_embs = embs / norms
    
    # Cosine similarity matrix
    sim_matrix = np.dot(norm_embs, norm_embs.T)
    
    # Calculate average distance for upper triangular part (excluding diagonal)
    n = len(norm_embs)
    distances = []
    for i in range(n):
        for j in range(i+1, n):
            distances.append(1.0 - sim_matrix[i, j])
            
    return float(np.mean(distances))
