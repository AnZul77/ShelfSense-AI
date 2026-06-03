import torch
import torch.nn as nn


class NeuralCollaborativeFiltering(nn.Module):

    def __init__(
        self,
        n_users,
        n_books,
        embedding_dim=50
    ):
        super().__init__()

        self.user_embedding = nn.Embedding(
            n_users,
            embedding_dim
        )

        self.book_embedding = nn.Embedding(
            n_books,
            embedding_dim
        )

        self.mlp = nn.Sequential(
            nn.Linear(
                embedding_dim * 2,
                64
            ),

            nn.ReLU(),

            nn.Linear(
                64,
                32
            ),

            nn.ReLU(),

            nn.Linear(
                32,
                1
            )
        )

    def forward(
        self,
        users,
        books
    ):

        user_emb = self.user_embedding(
            users
        )

        book_emb = self.book_embedding(
            books
        )

        x = torch.cat(
            [user_emb, book_emb],
            dim=1
        )

        output = self.mlp(x)

        return output.squeeze()