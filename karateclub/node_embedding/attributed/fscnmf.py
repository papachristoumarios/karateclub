import numpy as np
import networkx as nx
from scipy import sparse
from numpy.linalg import inv
from karateclub.estimator import Estimator

class FSCNMF(Estimator):
    r"""An implementation of `"FCNMF" <https://arxiv.org/pdf/1804.05313.pdf.>`_
    from the Arxiv '18 paper "Fusing Structure and Content via Non-negative Matrix
    Factorization for Embedding Information Networks". The procedure uses a joint 
    matrix factorization technique on the adjacency and feature matrices. The node
    and feature embeddings are co-regularized for alignment of the embedding spaces.
       
    Args:
        dimensions (int): Number of embedding dimensions. Default is 32.
        lower_control (float): Embedding score minimal value. Default is 10**-15.
        iterations (int): Power iterations. Default is 500.
        alpha_1 (float): Alignment parameter for adjacency matrix. Default is 1000.0.
        alpha_2 (float): Adjacency basis regularization. Default is 1.0.
        alpha_3 (float): Adjacency features regularization. Default is 1.0.
        beta_1 (float): Alignment parameter for feature matrix. Default is 1000.0.
        beta_2 (float): Attribute basis regularization. Default is 1.0.
        beta_3 (float): Attribute basis regularization. Default is 1.0.
    """
    def __init__(self, dimensions=32, lower_control=10**-15, iterations=500,
                 alpha_1=1000.0, alpha_2=1.0, alpha_3=1.0,
                 beta_1=1000.0, beta_2=1.0, beta_3=1.0):

        self.dimensions = dimensions
        self.lower_control = lower_control
        self.iterations = iterations
        self.alpha_1 = alpha_1
        self.alpha_2 = alpha_2
        self.alpha_3 = alpha_3
        self.beta_1 = beta_1
        self.beta_2 = beta_2
        self.beta_3 = beta_3

    def _init_weights(self):
        """
        Setup basis and feature matrices.
        """
        self.U = np.random.uniform(0, 1, (self.A.shape[0], self.dimensions))
        self.V = np.random.uniform(0, 1, (self.dimensions, self.X.shape[1]))
        self.B_1 = np.random.uniform(0, 1, (self.A.shape[0], self.dimensions))
        self.B_2 = np.random.uniform(0, 1, (self.dimensions, self.A.shape[0]))

    def _update_B1(self):
        """
        Update node bases.
        """
        simi_term = self.A.dot(np.transpose(self.B_2)) + self.alpha_1*self.U
        regul = self.alpha_1*np.eye(self.dimensions)
        regul = regul + self.alpha_2*np.eye(self.dimensions)
        covar_term = inv(np.dot(self.B_2, np.transpose(self.B_2))+regul)
        self.B_1 = np.dot(simi_term, covar_term)
        self.B_1[self.B_1 < self.lower_control] = self.lower_control

    def _update_B2(self):
        """
        Update node features.
        """
        to_inv = np.dot(np.transpose(self.B_1), self.B_1)
        to_inv = to_inv + self.alpha_3*np.eye(self.dimensions)
        covar_term = inv(to_inv)
        simi_term = self.A.dot(self.B_1).transpose()
        self.B_2 = covar_term.dot(simi_term)
        self.B_2[self.B_2 < self.lower_control] = self.lower_control

    def _update_U(self):
        """
        Update feature basis.
        """
        simi_term = self.X.dot(np.transpose(self.V)) + self.beta_1*self.B_1
        regul = self.beta_1*np.eye(self.dimensions)
        regul = regul + self.beta_2*np.eye(self.dimensions)
        covar_term = inv(np.dot(self.V, np.transpose(self.V))+regul)
        self.U = np.dot(simi_term, covar_term)
        self.U[self.U < self.lower_control] = self.lower_control

    def _update_V(self):
        """
        Update features.
        """
        to_inv = np.dot(np.transpose(self.U), self.U)
        to_inv = to_inv + self.beta_3*np.eye(self.dimensions)
        covar_term = inv(to_inv)
        simi_term = self.X.transpose().dot(self.U)
        self.V = np.dot(simi_term, covar_term).transpose()
        self.V[self.V < self.lower_control] = self.lower_control

    def _create_D_inverse(self, graph):
        """
        Creating a sparse inverse degree matrix.

        Arg types:
            * **graph** *(NetworkX graph)* - The graph to be embedded.

        Return types:
            * **D_inverse** *(Scipy array)* - Diagonal inverse degree matrix.
        """
        index = np.arange(graph.number_of_nodes())
        values = np.array([1.0/graph.degree[node] for node in range(graph.number_of_nodes())])
        shape = (graph.number_of_nodes(), graph.number_of_nodes())
        D_inverse = sparse.coo_matrix((values, (index, index)), shape=shape)
        return D_inverse

    def _create_base_matrix(self, graph):
        """
        Creating a normalized adjacency matrix.

        Return types:
            * **A_hat* - Normalized adjacency matrix.
        """
        A = nx.adjacency_matrix(graph, nodelist=range(graph.number_of_nodes()))
        D_inverse = self._create_D_inverse(graph)
        A_hat = D_inverse.dot(A)
        return A_hat

    def fit(self, graph, X):
        """
        Fitting a TENE model.

        Arg types:
            * **graph** *(NetworkX graph)* - The graph to be embedded.
            * **X** *(Scipy COO or Numpy array)* - The matrix of node features.
        """
        self._check_graph(graph)
        self.X = X
        self.A = self._create_base_matrix(graph)
        self._init_weights()
        for _ in range(self.iterations):
            self._update_B1()
            self._update_B2()
            self._update_U()
            self._update_V()

    def get_embedding(self):
        r"""Getting the node embedding.

        Return types:
            * **embedding** *(Numpy array)* - The embedding of nodes.
        """
        embedding = np.concatenate([self.B_1,self.U], axis=1)
        return embedding
